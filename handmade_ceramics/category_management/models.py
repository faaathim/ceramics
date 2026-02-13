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
        if not self.is_deleted:
            existing = Category.all_objects.filter(name__iexact=self.name.strip(), is_deleted=False)
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError({'name': 'A category with this name already exists.'})


    def save(self, *args, **kwargs):
        if not self.is_deleted:
            self.full_clean()
        super().save(*args, **kwargs)


    def soft_delete(self):

        # Soft delete category
        self.is_deleted = True
        self.is_listed = False
        self.save(update_fields=["is_deleted", "is_listed"])

        # Soft delete related products
        products = Product.all_objects.filter(category=self, is_deleted=False)

        for product in products:
            product.is_deleted = True
            product.is_listed = False
            product.save(update_fields=["is_deleted", "is_listed"])

            # Soft delete variants
            product.variants.update(is_deleted=True, is_listed=False)

