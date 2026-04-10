# category_management/models.py

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from product_management.models import Product
from cloudinary.models import CloudinaryField


class CategoryQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)


class CategoryManager(models.Manager):
    def get_queryset(self):
        return CategoryQuerySet(self.model, using=self._db).filter(is_deleted=False)


class Category(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    image = CloudinaryField('category_image', blank=True, null=True)

    is_listed = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    is_deleted = models.BooleanField(default=False)

    objects = CategoryManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def clean(self):
        name = self.name.strip()

        if not name:
            raise ValidationError({'name': "Category name cannot be empty."})

        if len(name) < 3:
            raise ValidationError({'name': "Category name must be at least 3 characters long."})

        if len(name) > 150:
            raise ValidationError({'name': "Category name cannot exceed 150 characters."})

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.full_clean()
        super().save(*args, **kwargs)

    def soft_delete(self):
        self.is_deleted = True
        self.is_listed = False
        self.save(update_fields=["is_deleted", "is_listed"])

        products = Product.all_objects.filter(category=self, is_deleted=False)

        products.update(is_deleted=True, is_listed=False)

        from product_management.models import Variant
        Variant.objects.filter(product__in=products).update(
            is_deleted=True,
            is_listed=False
        )