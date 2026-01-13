from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from product_management.models import Variant

User = get_user_model()


class Wishlist(models.Model):
    """
    One row = one variant wishlisted by one user.
    Together, these rows represent the user's single wishlist.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'variant')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user} ❤️ {self.variant}"
