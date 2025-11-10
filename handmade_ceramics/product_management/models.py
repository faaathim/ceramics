import os
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count
from PIL import Image

User = get_user_model()

def product_image_upload_path(instance, filename):
    """Store images under media/products/<product_id>/<filename>"""
    product_id = instance.product.id if getattr(instance, 'product', None) and instance.product.id else 'new'
    return f'products/{product_id}/{filename}'

def main_image_upload_path(instance, filename):
    """Store main images under media/products/main/<product_id>_main_<filename>"""
    pid = instance.id or 'new'
    return f'products/main/{pid}_main_{filename}'

class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)

class ProductManager(models.Manager):
    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db).filter(is_deleted=False)

class Product(models.Model):
    name = models.CharField(max_length=255)  
    description = models.TextField(blank=True)
    category = models.ForeignKey('category_management.Category', on_delete=models.PROTECT, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=1)
    main_image = models.ImageField(upload_to=main_image_upload_path, blank=True, null=True)
    is_listed = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    objects = ProductManager()      
    all_objects = models.Manager() 

    class Meta:
        ordering = ['-created_at'] 

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=product_image_upload_path)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']

class Review(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.PositiveSmallIntegerField(default=5)  # 1..5
    title = models.CharField(max_length=120, blank=True)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=True)  # admin can moderate

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} - {self.rating} by {self.user or 'anonymous'}"


def product_average_rating(product):
    """Return (avg_rating, count) for a product."""
    agg = product.reviews.filter(is_approved=True).aggregate(avg=Avg('rating'), count=Count('id'))
    return (round(agg['avg'] or 0, 2), agg['count'] or 0)

def get_related_products(product, limit=6):
    qs = Product.objects.filter(category=product.category, is_listed=True).exclude(pk=product.pk).order_by('-created_at')[:limit]
    return qs