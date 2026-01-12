from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)

    discount_percentage = models.PositiveIntegerField(
        help_text="Example: 10 means 10% discount"
    )

    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    is_active = models.BooleanField(default=True)
    expiry_date = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        """
        Check coupon active & expiry
        """
        return self.is_active and self.expiry_date >= timezone.now()

    def __str__(self):
        return self.code


class CouponUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE)

    used_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        unique_together = ('user', 'coupon')

    def __str__(self):
        return f"{self.user} used {self.coupon.code}"
