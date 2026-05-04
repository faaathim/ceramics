from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings

class PricingService:
    @staticmethod
    def quantify(amount):
        return Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_order_totals(cls, order):
        from orders.models import OrderItem

        active_items = order.items.exclude(
            item_status__in=['CANCELLED', 'RETURNED']
        )

        subtotal = sum((item.item_total for item in active_items), Decimal("0.00"))
        subtotal = cls.quantify(subtotal)

        discount = cls.calculate_dynamic_discount(subtotal, order.coupon)
        discount = cls.quantify(discount)

        if subtotal > 0:
            for item in active_items:
                proportion = item.item_total / subtotal
                item_discount = discount * proportion

                item.coupon_discount_amount = cls.quantify(item_discount)
                item.final_total = cls.quantify(item.item_total - item.coupon_discount_amount)

                item.save(update_fields=['coupon_discount_amount', 'final_total'])

        shipping = cls.calculate_shipping(subtotal)
        shipping = cls.quantify(shipping)

        tax = cls.quantify(Decimal("0.00"))

        return {
            'subtotal': subtotal,
            'discount_amount': discount,
            'shipping_charge': shipping,
            'tax_amount': tax,
            'total_amount': cls.quantify(subtotal + shipping + tax - discount)
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