from django.db import models
from django.utils import timezone
from django.db.models import Avg, Count, Sum
from decimal import Decimal

from cloudinary.models import CloudinaryField
from django.contrib.auth import get_user_model

User = get_user_model()



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

    # ✅ Keep price only here
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # ✅ Total stock (sum of variants)
    stock = models.PositiveIntegerField(default=0, editable=False)

    # ✅ Only one image for product list
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

    # ✅ Sum of all variant stock
    def update_stock(self):
        total = self.variants.filter(
            is_deleted=False
        ).aggregate(total=Sum('stock'))['total'] or 0

        if self.stock != total:
            Product.all_objects.filter(pk=self.pk).update(stock=total)
            self.stock = total

    def can_be_listed(self):
        return self.variants.filter(is_deleted=False, is_listed=True).exists()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.can_be_listed():
            Product.all_objects.filter(pk=self.pk).update(
                stock=0,
                is_listed=False
            )


    def get_active_product_offer(self):
        now = timezone.now()
        return self.product_offers.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('-discount_percentage').first()

    def get_active_category_offer(self):
        now = timezone.now()
        return self.category.category_offers.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('-discount_percentage').first()

    def get_best_discount_percentage(self):
        product_offer = self.get_active_product_offer()
        category_offer = self.get_active_category_offer()

        return max(
            product_offer.discount_percentage if product_offer else 0,
            category_offer.discount_percentage if category_offer else 0
        )

    def get_discounted_price(self):
        discount_percentage = self.get_best_discount_percentage()

        if discount_percentage == 0:
            return self.price

        discount_amount = (Decimal(discount_percentage) / Decimal('100')) * self.price
        final_price = self.price - discount_amount

        return final_price.quantize(Decimal('0.01'))


class Variant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants'
    )

    # ✅ simple + enforced
    color = models.CharField(max_length=64)

    stock = models.PositiveIntegerField(default=0)

    is_listed = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'color')  # ✅ prevent duplicate colors

    def __str__(self):
        return f"{self.product.name} — {self.color}"

    def save(self, *args, **kwargs):
        # auto unlist if no stock
        if self.stock == 0:
            self.is_listed = False

        super().save(*args, **kwargs)

        # update product stock
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

    # first image = main image
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