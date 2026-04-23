from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings

class PricingService:
    """
    Centralized service for all order pricing, shipping, and discount calculations.
    Addresses architectural flaws by recalculating state dynamically rather than relying on stale data.
    """

    @staticmethod
    def quantify(amount):
        """Standard financial rounding to 2 decimal places."""
        return Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_order_totals(cls, order):
        from orders.models import OrderItem

        active_items = order.items.exclude(
            item_status__in=['CANCELLED', 'RETURNED']
        )

        # 1. Subtotal
        subtotal = sum((item.item_total for item in active_items), Decimal("0.00"))
        subtotal = cls.quantify(subtotal)

        # 2. Discount
        discount = cls.calculate_dynamic_discount(subtotal, order.coupon)
        discount = cls.quantify(discount)

        # 🔥 3. DISTRIBUTE DISCOUNT TO ITEMS (FIX)
        if subtotal > 0:
            for item in active_items:
                proportion = item.item_total / subtotal
                item_discount = discount * proportion

                item.coupon_discount_amount = cls.quantify(item_discount)
                item.final_total = cls.quantify(item.item_total - item.coupon_discount_amount)

                item.save(update_fields=['coupon_discount_amount', 'final_total'])

        # 4. Shipping
        shipping = cls.calculate_shipping(subtotal)
        shipping = cls.quantify(shipping)

        # 5. Tax
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
        """
        Calculates the discount dynamically. 
        Supports percentage-based coupons and can be extended for fixed amounts or caps.
        """
        if not coupon or subtotal <= 0:
            return Decimal("0.00")

        # Check eligibility with "grace" or custom rules
        if not cls.is_eligible_for_coupon(subtotal, coupon):
            return Decimal("0.00")

        # Currently only percentage coupons are supported in the model
        percentage = Decimal(str(coupon.discount_percentage))
        discount = (subtotal * percentage) / Decimal("100")
        
        # Future-proofing: If coupon has a max_discount_cap, apply it here
        # if hasattr(coupon, 'max_discount') and coupon.max_discount:
        #    discount = min(discount, coupon.max_discount)

        return cls.quantify(discount)

    @staticmethod
    def is_eligible_for_coupon(subtotal, coupon):
        """
        Validates if the current subtotal meets the coupon requirements.
        Allows for 'grace logic' (e.g., if subtotal is within 1% of threshold).
        """
        threshold = coupon.min_order_amount
        
        # Simple threshold check for now, but centralized here for easy modification
        return subtotal >= threshold

    @staticmethod
    def calculate_shipping(subtotal):
        """
        Standardized shipping rules.
        """
        if subtotal <= 0:
            return Decimal("0.00")
            
        # Example rule: Free shipping over 1000
        free_shipping_threshold = getattr(settings, 'FREE_SHIPPING_THRESHOLD', Decimal("1000.00"))
        
        if subtotal >= free_shipping_threshold:
            return Decimal("0.00")
        
        return Decimal(str(getattr(settings, 'DELIVERY_CHARGE', 50)))
