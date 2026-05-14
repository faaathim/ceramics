from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


class OfferBase(models.Model):
    """
    Shared validation logic for ProductOffer & CategoryOffer
    """
    discount_percentage = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(90)
        ]
    )

    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def validate_dates(self):
        now = timezone.now()

        if self.start_date is None or self.end_date is None:
            raise ValidationError("Start and end dates are required.")

        # start must be before end
        if self.end_date <= self.start_date:
            raise ValidationError({
                "end_date": "End date must be after start date."
            })

        # allow small flexibility: prevent only clearly past start dates
        if self.start_date < now - timezone.timedelta(minutes=1):
            raise ValidationError({
                "start_date": "Start date cannot be in the past."
            })

    def validate_overlap(self, model_class, filter_field, value):
        """
        Prevent overlapping active offers
        """
        if not self.is_active:
            return

        existing = model_class.objects.filter(
            is_active=True
        ).filter(**{filter_field: value})

        if self.pk:
            existing = existing.exclude(pk=self.pk)

        # overlap condition
        overlapping = existing.filter(
            start_date__lt=self.end_date,
            end_date__gt=self.start_date
        )

        if overlapping.exists():
            raise ValidationError(
                "An active offer already exists for this period."
            )

    def is_valid(self):
        now = timezone.now()
        return (
            self.is_active and
            self.start_date <= now <= self.end_date
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ProductOffer(OfferBase):
    product = models.ForeignKey(
        'product_management.Product',
        on_delete=models.CASCADE,
        related_name='product_offers'
    )

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        super().validate_dates()
        super().validate_overlap(
            ProductOffer,
            "product",
            self.product
        )

    def __str__(self):
        return f"{self.product.name} - {self.discount_percentage}%"


class CategoryOffer(OfferBase):
    category = models.ForeignKey(
        'category_management.Category',
        on_delete=models.CASCADE,
        related_name='category_offers'
    )

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        super().validate_dates()
        super().validate_overlap(
            CategoryOffer,
            "category",
            self.category
        )

    def __str__(self):
        return f"{self.category.name} - {self.discount_percentage}%"