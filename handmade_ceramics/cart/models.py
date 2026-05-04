# cart/models.py

from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from product_management.models import Variant

User = get_user_model()


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Cart({self.user.username})"

    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    def total_price(self):
        total = 0
        for item in self.items.select_related('variant__product'):
            price = item.variant.product.get_discounted_price()
            total += price * item.quantity
        return total



class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('cart', 'variant')

    def __str__(self):
        return f"{self.variant} x {self.quantity}"
