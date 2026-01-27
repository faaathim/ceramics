# payments/models.py

from django.db import models
from django.utils import timezone

from orders.models import Order


PAYMENT_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('SUCCESS', 'Success'),
    ('FAILED', 'Failed'),
]

PAYMENT_GATEWAY_CHOICES = [
    ('RAZORPAY', 'Razorpay'),
    ('PAYPAL', 'PayPal'),
]


class Payment(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    gateway = models.CharField(
        max_length=20,
        choices=PAYMENT_GATEWAY_CHOICES
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=10,
        default='INR'
    )

    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING'
    )

    # Razorpay specific fields
    razorpay_order_id = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    razorpay_payment_id = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    razorpay_signature = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order.order_id} | {self.gateway} | {self.status}"
