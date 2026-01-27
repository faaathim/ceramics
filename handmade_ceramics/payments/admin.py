# payments/admin.py

from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'order',
        'gateway',
        'amount',
        'status',
        'created_at',
    )
    list_filter = ('gateway', 'status')
    search_fields = ('order__order_id', 'razorpay_order_id')
