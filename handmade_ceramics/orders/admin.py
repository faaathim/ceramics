# orders/admin.py

from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('product_name', 'variant_color', 'unit_price', 'quantity', 'item_total', 'item_status')
    extra = 0
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'total_amount', 'status', 'created_at')
    search_fields = ('order_id', 'user__username', 'shipping_full_name', 'shipping_phone')
    list_filter = ('status', 'payment_method', 'created_at')
    inlines = [OrderItemInline]
    readonly_fields = ('order_id', 'created_at', 'updated_at')
