# orders/services/return_service.py

from django.db import transaction
from decimal import Decimal
from orders.services.refund_service import RefundService


class ReturnService:

    @staticmethod
    @transaction.atomic
    def approve_order_return(order):

        if order.status not in ["RETURN_REQUESTED", "PARTIAL_RETURN_REQUESTED"]:
            return False

        order.status = "RETURN_PROCESSING"

        order.items.filter(
            item_status="RETURN_REQUESTED"
        ).update(item_status="RETURN_PROCESSING")

        order.save()
        return True


    @staticmethod
    @transaction.atomic
    def reject_order_return(order, reason=""):

        if order.status not in ["RETURN_REQUESTED", "PARTIAL_RETURN_REQUESTED"]:
            return False

        order.status = "DELIVERED"
        order.return_rejection_reason = reason

        order.items.filter(
            item_status="RETURN_REQUESTED"
        ).update(item_status="DELIVERED")

        order.save()
        return True


    @staticmethod
    @transaction.atomic
    def complete_order_return(order):

        items = order.items.filter(item_status='RETURN_PROCESSING')

        if not items.exists():
            return False

        # ✅ SINGLE SOURCE OF TRUTH FOR REFUND
        total_refund = sum(
            (item.final_total for item in items),
            Decimal("0.00")
        )

        # ✅ Refund ONLY ONCE
        if total_refund > 0:
            RefundService.refund_to_wallet(
                user=order.user,
                amount=total_refund,
                order=order,
                source='RETURN_REFUND'
            )

        # ✅ Mark returned
        items.update(item_status='RETURNED')

        order.status = 'RETURNED'
        order.is_refunded = True

        # ❌ REMOVE THIS (VERY IMPORTANT)
        # order.recalculate_totals()

        order.save()

        return True