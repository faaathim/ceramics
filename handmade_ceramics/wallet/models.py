# wallet/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from orders.models import Order
import uuid

User = get_user_model()

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - Wallet"


class WalletTransaction(models.Model):

    CREDIT = 'CREDIT'
    DEBIT = 'DEBIT'

    TRANSACTION_TYPE_CHOICES = [
        (CREDIT, 'Credit'),
        (DEBIT, 'Debit'),
    ]

    SOURCE_CHOICES = [
        ('ORDER_PAYMENT', 'Order Payment'),
        ('CANCEL_REFUND', 'Cancel Refund'),
        ('RETURN_REFUND', 'Return Refund'),
        ('MANUAL', 'Manual Adjustment'),
    ]

    transaction_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')

    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPE_CHOICES
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='MANUAL'
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    description = models.TextField()

    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_id} - {self.transaction_type} - {self.amount}"
