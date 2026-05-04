from django.db import transaction
from decimal import Decimal

from .refund_service import RefundService
from wallet.models import Wallet, WalletTransaction


class OrderService:

    @staticmethod
    @transaction.atomic
    def cancel_item(item):

        # ✅ Prevent duplicate cancel
        if item.item_status in ['CANCELLED', 'RETURNED']:
            return

        order = item.order

        # ✅ Capture refund BEFORE mutation
        refund_amount = item.final_total

        # ✅ Cancel item (this may call recalculate_totals internally — fine now)
        item.cancel_item()

        # 🔥 IMPORTANT: do NOT rely on recalculated values
        if order.is_paid and refund_amount > 0:

            RefundService.refund_to_wallet(
                user=order.user,
                amount=refund_amount,
                order=order,
                source="ITEM_CANCEL_REFUND"
            )


    @staticmethod
    @transaction.atomic
    def cancel_order(order):

        # ✅ Prevent duplicate cancel
        if order.status in ["CANCELLED", "RETURNED"]:
            return

        # ✅ Get only active items
        refundable_items = order.items.exclude(
            item_status__in=["CANCELLED", "RETURNED"]
        )

        if not refundable_items.exists():
            return

        # ✅ Calculate refund BEFORE any modification
        refund_amount = sum(
            (item.final_total for item in refundable_items),
            Decimal("0.00")
        )

        # ✅ Cancel all items
        for item in refundable_items:
            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save()

            item.item_status = "CANCELLED"
            item.save()

        # ✅ Update order
        order.status = "CANCELLED"
        order.is_refunded = True
        order.save()

        # ✅ Refund ONLY what user actually paid (NO shipping)
        if order.is_paid and refund_amount > 0:

            RefundService.refund_to_wallet(
                user=order.user,
                amount=refund_amount,
                order=order,
                source="ORDER_CANCEL_REFUND"
            )


    @staticmethod
    @transaction.atomic
    def process_item_return(item):

        # ✅ Only valid state
        if item.item_status != 'RETURN_REQUESTED':
            return

        order = item.order

        # ✅ Capture refund BEFORE mutation
        refund_amount = item.final_total

        # ✅ Process return (updates stock + status)
        item.process_return()

        if order.is_paid and refund_amount > 0:

            RefundService.refund_to_wallet(
                user=order.user,
                amount=refund_amount,
                order=order,
                source="ITEM_RETURN_REFUND"
            )