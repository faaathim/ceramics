# orders/services/pricing_service

from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings

class PricingService:

    @staticmethod
    def quantify(amount):
        return Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_order_totals(cls, order):

        active_items = order.items.exclude(
            item_status__in=['CANCELLED', 'RETURNED']
        )

        subtotal = sum((item.item_total for item in active_items), Decimal("0.00"))

        discount = sum((item.coupon_discount_amount for item in active_items), Decimal("0.00"))

        final_items_total = sum((item.final_total for item in active_items), Decimal("0.00"))

        shipping = cls.calculate_shipping(subtotal)

        tax = Decimal("0.00")

        return {
            'subtotal': subtotal,
            'discount_amount': discount,
            'shipping_charge': shipping,
            'tax_amount': tax,
            'total_amount': final_items_total + shipping + tax
        }

    @classmethod
    def calculate_dynamic_discount(cls, subtotal, coupon):
        if not coupon or subtotal <= 0:
            return Decimal("0.00")

        if not cls.is_eligible_for_coupon(subtotal, coupon):
            return Decimal("0.00")

        percentage = Decimal(str(coupon.discount_percentage))
        discount = (subtotal * percentage) / Decimal("100")

        return cls.quantify(discount)

    @staticmethod
    def is_eligible_for_coupon(subtotal, coupon):
        return subtotal >= coupon.min_order_amount

    @staticmethod
    def calculate_shipping(subtotal):
        if subtotal <= 0:
            return Decimal("0.00")

        threshold = Decimal(str(getattr(settings, 'FREE_SHIPPING_THRESHOLD', 1000)))
        delivery_charge = Decimal(str(getattr(settings, 'DELIVERY_CHARGE', 100)))

        if subtotal < threshold:
            return delivery_charge

        return Decimal("0.00")