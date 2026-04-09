from django.db import models
from django.conf import settings
from product_management.models import Product
from django.db.models import Avg, Count


User = settings.AUTH_USER_MODEL


class Review(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    rating = models.PositiveSmallIntegerField()
    comment = models.TextField()

    is_approved = models.BooleanField(default=True)

    # Soft delete
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} - {self.user}"
    

def update_product_rating(product):
    agg = product.reviews.filter(
        is_approved=True,
        is_deleted=False
    ).aggregate(
        avg=Avg('rating'),
        count=Count('id')
    )

    product.average_rating = round(agg['avg'] or 0, 2)
    product.review_count = agg['count'] or 0
    product.save(update_fields=['average_rating', 'review_count'])