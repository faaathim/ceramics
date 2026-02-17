from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

class ProductOffer(models.Model):
    product = models.ForeignKey(
        'product_management.Product',
        on_delete=models.CASCADE,
        related_name='product_offers'
    )
    discount_percentage = models.PositiveIntegerField(
        help_text="Enter discount percentage (Example: 20 for 20%)"
    )
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def is_valid(self):
        now = timezone.now()
        return (self.is_active and self.start_date <= now <= self.end_date)

    def clean(self):
        if self.is_active:
            existing = ProductOffer.objects.filter(
                product=self.product,
                is_active=True
            )

            if self.pk:
                existing = existing.exclude(pk=self.pk)

            if existing.exists():
                raise ValidationError(
                    "An active offer already exists for this product."
                )

    def __str__(self):
        return f"{self.product.name} - {self.discount_percentage}%"

    

class CategoryOffer(models.Model):
    category = models.ForeignKey('category_management.Category', on_delete=models.CASCADE, related_name='category_offers')
    discount_percentage = models.PositiveIntegerField(help_text="Enter discount percentage (Example: 30 for 30%)")
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def is_valid(self):
        now = timezone.now()
        return (self.is_active and self.start_date <= now <= self.end_date)
    
    def clean(self):
        if self.is_active:
            existing = CategoryOffer.objects.filter(
                category = self.category,
                is_active = True
            )

            if self.pk:
                existing = existing.exclude(pk=self.pk)

            if existing.exists():
                raise ValidationError("An active offer already exists for this category.")
    
    def __str__(self):
        return f"{self.category.name} - {self.discount_percentage}%"