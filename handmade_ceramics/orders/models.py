from django.db import models, transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.crypto import get_random_string
from coupons.models import Coupon

from product_management.models import Variant, Product

User = get_user_model()

ORDER_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('CONFIRMED', 'Confirmed'),
    ('SHIPPED', 'Shipped'),
    ('OUT_FOR_DELIVERY', 'Out for delivery'),
    ('DELIVERED', 'Delivered'),
    ('RETURN_REQUESTED', 'Return requested'),
    ('RETURN_PROCESSING', 'Return processing'),
    ('RETURNED', 'Returned'),
    ('CANCELLED', 'Cancelled'),
]


def generate_order_id():
    date_part = timezone.now().strftime('%Y%m%d')
    random_part = get_random_string(6).upper()
    return f"ORD{date_part}-{random_part}"


class Order(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')

    order_id = models.CharField(max_length=40, unique=True, editable=False)

    shipping_full_name = models.CharField(max_length=200)
    shipping_phone = models.CharField(max_length=30)
    shipping_email = models.EmailField()
    shipping_address_line = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_pincode = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100, default='India')

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    payment_method = models.CharField(max_length=50, default='COD')
    is_paid = models.BooleanField(default=False)
    is_refunded = models.BooleanField(default=False)
    status = models.CharField(max_length=30, choices=ORDER_STATUS_CHOICES, default='PENDING')

    cancellation_reason = models.TextField(blank=True, null=True)
    return_reason = models.TextField(blank=True, null=True)
    return_rejection_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    ORDER_STATUS_FLOW = {
        'PENDING': ['CONFIRMED', 'CANCELLED'],
        'CONFIRMED': ['SHIPPED', 'CANCELLED'],
        'SHIPPED': ['OUT_FOR_DELIVERY'],
        'OUT_FOR_DELIVERY': ['DELIVERED'],
        'DELIVERED': ['RETURN_REQUESTED'],
        'RETURN_REQUESTED': ['RETURN_PROCESSING', 'DELIVERED'],
        'RETURN_PROCESSING': ['RETURNED'],
        'RETURNED': [],
        'CANCELLED': [],
    }

    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.order_id} - {self.user}"


    def save(self, *args, **kwargs):
        if not self.order_id:
            for _ in range(5):
                candidate = generate_order_id()
                if not Order.objects.filter(order_id=candidate).exists():
                    self.order_id = candidate
                    break
            else:
                self.order_id = generate_order_id()
        super().save(*args, **kwargs)


    def get_absolute_url(self):
        return reverse('orders:order_detail', args=[self.order_id])


    def can_change_status(self, new_status):
        return new_status in self.ORDER_STATUS_FLOW.get(self.status, [])


class OrderItem(models.Model):

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    variant = models.ForeignKey(Variant, on_delete=models.SET_NULL, null=True, blank=True)

    product_name = models.CharField(max_length=255)
    variant_color = models.CharField(max_length=100, blank=True)

    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity = models.PositiveIntegerField(default=1)
    item_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    item_status = models.CharField(max_length=30, choices=ORDER_STATUS_CHOICES, default='PENDING')

    cancellation_reason = models.TextField(blank=True, null=True)
    return_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product_name} x {self.quantity} ({self.order.order_id})"


    def save(self, *args, **kwargs):
        self.item_total = self.unit_price * self.quantity
        super().save(*args, **kwargs)