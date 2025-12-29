# product_management/models.py
import os
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.db.models import Avg, Count, Sum
from PIL import Image

# NOTE: keep get_user_model import only if you need User in this file
from django.contrib.auth import get_user_model
User = get_user_model()


def product_image_upload_path(instance, filename):
    product_id = instance.product.id if getattr(instance, 'product', None) and instance.product.id else 'new'
    return f'products/{product_id}/{filename}'


def main_image_upload_path(instance, filename):
    pid = instance.id or 'new'
    return f'products/main/{pid}_main_{filename}'


def variant_main_upload_path(instance, filename):
    pid = instance.product.id or 'new'
    vid = instance.id or 'new'
    return f'products/{pid}/variants/{vid}/main_{filename}'


def variant_image_upload_path(instance, filename):
    # instance.variant is used for variant images
    pid = instance.variant.product.id or 'new'
    vid = instance.variant.id or 'new'
    return f'products/{pid}/variants/{vid}/{filename}'


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)


class ProductManager(models.Manager):
    def get_queryset(self):
        return (
            ProductQuerySet(self.model, using=self._db)
            .filter(
                is_deleted=False,
                category__is_deleted=False
            )
        )



class Product(models.Model):
    """
    Product holds product-level information (name, description, category, price).
    Variants (colors, sizes) are separate and linked via Variant model.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey('category_management.Category', on_delete=models.PROTECT, related_name='products')
    # Price is stored on Product (you told me all variants share same price)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # stock is computed from variants (not editable manually)
    stock = models.PositiveIntegerField(default=0, editable=False)

    main_image = models.ImageField(upload_to=main_image_upload_path, blank=True, null=True)
    is_listed = models.BooleanField(default=False)  # whether product is shown on shop
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    objects = ProductManager()   # default manager excludes deleted
    all_objects = models.Manager()  # use when you need to access deleted ones

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    # ---------------------
    # Stock & listing helpers
    # ---------------------
    def update_stock(self):
        """
        Recalculate total stock from non-deleted variants.
        This writes to DB without triggering save() side-effects.
        """
        total = self.variants.filter(is_deleted=False).aggregate(total=Sum('stock'))['total'] or 0
        # Write directly to DB through all_objects to avoid recursion with save()
        if self.stock != total:
            Product.all_objects.filter(pk=self.pk).update(stock=total)
            self.stock = total

    def can_be_listed(self):
        """
        Product can be listed only if it has at least one non-deleted variant.
        """
        return self.variants.filter(is_deleted=False).exists()

    # ---------------------
    # Convenience helpers for templates / views
    # ---------------------
    def get_default_variant(self):
        """
        Return the default variant to show in the shop card:
        - We pick the latest listed variant (is_listed=True) as you requested (A=1).
        - Returns None if no suitable variant exists.
        """
        return self.variants.filter(is_deleted=False, is_listed=True).order_by('-created_at').first()

    def get_variant_by_color(self, color):
        """
        Return a variant of this product matching the color (case-insensitive).
        Useful for linking color swatches.
        """
        if not color:
            return None
        return self.variants.filter(is_deleted=False, color__iexact=color).first()

    def listed_variants(self):
        """
        Convenience queryset of variants that are listed and not deleted.
        Use in views if you want to iterate quickly.
        """
        return self.variants.filter(is_deleted=False, is_listed=True)

    def save(self, *args, **kwargs):
        """
        Ensure product is unlisted and stock is 0 if there are no variants.
        Keep normal save behavior otherwise.
        """
        super().save(*args, **kwargs)
        if not self.can_be_listed():
            Product.all_objects.filter(pk=self.pk).update(stock=0, is_listed=False)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=product_image_upload_path)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']


class Variant(models.Model):
    """
    Variant belongs to a Product and represents a sellable SKU (e.g., color).
    Note: price is on Product (shared by all variants).
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    color = models.CharField(max_length=64, blank=True)  # e.g. "Pink", "Blue"
    main_image = models.ImageField(upload_to=variant_main_upload_path, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    is_listed = models.BooleanField(default=True)  # whether variant is visible / buyable
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)  # soft delete flag for variants

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} — {self.color or 'variant'} (#{self.pk})"

    def can_be_listed(self):
        """A variant can be listed only if it has stock > 0."""
        return self.stock > 0

    def save(self, *args, **kwargs):
        # If stock is 0, ensure variant isn't listed
        if self.stock == 0:
            self.is_listed = False

        super().save(*args, **kwargs)

        # Attempt to update product stock after variant changes (best-effort)
        try:
            self.product.update_stock()
        except Exception:
            # swallow exceptions to avoid blocking save() in edge-cases
            pass


class VariantImage(models.Model):
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=variant_image_upload_path)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']


# ---------------------
# Utility helpers
# ---------------------
def product_average_rating(product):
    """
    Compute average rating and count for a product (only approved reviews).
    Returns (avg, count)
    """
    agg = product.reviews.filter(is_approved=True).aggregate(
        avg=Avg('rating'),
        count=Count('id')
    )
    return (round(agg['avg'] or 0, 2), agg['count'] or 0)


def get_related_products(product, limit=6):
    """
    Return other listed products in the same category (exclude the product itself).
    """
    qs = Product.objects.filter(
        category=product.category,
        is_listed=True
    ).exclude(pk=product.pk).order_by('-created_at')[:limit]
    return qs
