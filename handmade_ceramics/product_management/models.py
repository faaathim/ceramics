from django.db import models
from django.utils import timezone
from django.db.models import Avg, Count, Sum
from decimal import Decimal

from cloudinary.models import CloudinaryField
from django.contrib.auth import get_user_model
from django.utils import timezone

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
    
    def get_active_product_offer(self):
        now = timezone.now()
        offer = self.product_offers.filter(
            is_active=True, start_date__lte=now, end_date__gte=now
            ).order_by('-discount_percentage').first()

        return offer
    
    def get_active_category_offer(self):
        now = timezone.now()
        offer = self.category.category_offers.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('-discount_percentage').first()

        return offer

    def get_best_discount_percentage(self):
        product_offer = self.get_active_product_offer()
        category_offer = self.get_active_category_offer()

        product_discount = product_offer.discount_percentage if product_offer else 0 
        category_discount = category_offer.discount_percentage if category_offer else 0

        return max(product_discount, category_discount)
    
    def get_discounted_price(self):
        discount_percentage = self.get_best_discount_percentage()

        if discount_percentage == 0:
            return self.price

        discount_percentage = Decimal(discount_percentage)
        discount_amount = (discount_percentage / Decimal('100')) * self.price

        final_price = self.price - discount_amount

        return final_price.quantize(Decimal('0.01'))


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
