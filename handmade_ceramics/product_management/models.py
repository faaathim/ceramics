from django.db import models
from django.utils import timezone
from django.db.models import Avg, Count, Sum

from cloudinary.models import CloudinaryField
from django.contrib.auth import get_user_model

User = get_user_model()



def main_image_upload_path(instance, filename):
    return f'products/main/{filename}'


def product_image_upload_path(instance, filename):
    """
    ⚠️ DO NOT DELETE THIS FUNCTION
    This is required for OLD migrations.
    It is NOT used anymore.
    """
    return f'products/extra/{filename}'


def variant_main_upload_path(instance, filename):
    pid = instance.product.id if instance.product_id else 'new'
    vid = instance.id or 'new'
    return f'products/{pid}/variants/{vid}/main_{filename}'


def variant_image_upload_path(instance, filename):
    pid = instance.variant.product.id if instance.variant_id else 'new'
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
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        'category_management.Category',
        on_delete=models.PROTECT,
        related_name='products'
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    stock = models.PositiveIntegerField(default=0, editable=False)

    main_image = CloudinaryField('product_main_image', blank=True, null=True)

    is_listed = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    objects = ProductManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def update_stock(self):
        total = self.variants.filter(
            is_deleted=False
        ).aggregate(total=Sum('stock'))['total'] or 0

        if self.stock != total:
            Product.all_objects.filter(pk=self.pk).update(stock=total)
            self.stock = total

    def can_be_listed(self):
        return self.variants.filter(is_deleted=False).exists()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.can_be_listed():
            Product.all_objects.filter(pk=self.pk).update(
                stock=0,
                is_listed=False
            )


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = CloudinaryField('product_image')
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']


class Variant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    color = models.CharField(max_length=64, blank=True)

    main_image = CloudinaryField('variant_main_image', blank=True, null=True)

    stock = models.PositiveIntegerField(default=0)
    is_listed = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} — {self.color or 'variant'}"

    def save(self, *args, **kwargs):
        if self.stock == 0:
            self.is_listed = False

        super().save(*args, **kwargs)

        try:
            self.product.update_stock()
        except Exception:
            pass


class VariantImage(models.Model):
    variant = models.ForeignKey(
        Variant,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = CloudinaryField('variant_image')
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']



def product_average_rating(product):
    agg = product.reviews.filter(
        is_approved=True
    ).aggregate(
        avg=Avg('rating'),
        count=Count('id')
    )
    return (round(agg['avg'] or 0, 2), agg['count'] or 0)


def get_related_products(product, limit=6):
    return Product.objects.filter(
        category=product.category,
        is_listed=True
    ).exclude(pk=product.pk).order_by('-created_at')[:limit]
