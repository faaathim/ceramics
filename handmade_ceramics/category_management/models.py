import os
from io import BytesIO
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from PIL import Image


def category_image_path(instance, filename):
    return f"categories/{instance.id or 'new'}/{filename}"


class CategoryQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)


class CategoryManager(models.Manager):
    def get_queryset(self):
        return CategoryQuerySet(self.model, using=self._db).filter(is_deleted=False)


class Category(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to=category_image_path, blank=True, null=True)
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
            existing = Category.all_objects.filter(
                name__iexact=self.name.strip(), is_deleted=False
            )
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError({'name': 'A category with this name already exists.'})

    def save(self, *args, **kwargs):
        if not self.is_deleted:
            self.full_clean()

        if self.pk is None and self.image:
            saved_image = self.image
            self.image = None
            super().save(*args, **kwargs)
            self.image = saved_image

        super().save(*args, **kwargs)

        if self.image:
            try:
                img_path = self.image.path
                img = Image.open(img_path)
                img = img.convert('RGB')
                width, height = img.size
                new_edge = min(width, height)
                left = (width - new_edge) / 2
                top = (height - new_edge) / 2
                right = (width + new_edge) / 2
                bottom = (height + new_edge) / 2
                img = img.crop((left, top, right, bottom))
                img = img.resize((800, 800), Image.LANCZOS)
                img.save(img_path, format='JPEG', quality=85)
            except Exception:
                pass
