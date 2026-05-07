# category_management/models.py

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from product_management.models import Product


class CategoryQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)


class CategoryManager(models.Manager):
    def get_queryset(self):
        return CategoryQuerySet(self.model, using=self._db).filter(is_deleted=False)


class Category(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

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
        errors = {}

        name = self.name.strip()

        if not name:
            errors['name'] = "Category name cannot be empty."

        elif len(name) < 3:
            errors['name'] = "Category name must be at least 3 characters long."

        elif len(name) > 150:
            errors['name'] = "Category name cannot exceed 150 characters."

        if self.description and len(self.description.strip()) > 500:
            errors['description'] = "Description cannot exceed 500 characters."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.name = self.name.strip()

        if self.description:
            self.description = self.description.strip()

        self.full_clean()
        super().save(*args, **kwargs)

    def soft_delete(self):
        self.is_deleted = True
        self.is_listed = False
        self.save(update_fields=["is_deleted", "is_listed"])

        products = Product.all_objects.filter(
            category=self,
            is_deleted=False
        )

        products.update(
            is_deleted=True,
            is_listed=False
        )

        from product_management.models import Variant

        Variant.objects.filter(product__in=products).update(
            is_deleted=True,
            is_listed=False
        )