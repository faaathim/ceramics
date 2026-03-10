from django.db import transaction
from orders.models import OrderItem
from .refund_service import RefundService


class OrderService:

    @staticmethod
    @transaction.atomic
    def cancel_item(item):

        order = item.order

        if item.item_status in ["CANCELLED", "RETURNED"]:
            return

        old_total = order.total_amount

        # restore stock
        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save()

        item.item_status = "CANCELLED"
        item.save()

        order.recalculate_totals()

        refund_amount = order.calculate_refund(old_total)

        if order.is_paid:
            RefundService.refund_to_wallet(
                user=order.user,
                amount=refund_amount,
                order=order,
                source="CANCEL_REFUND"
            )


@staticmethod
@transaction.atomic
def process_item_return(item):

    order = item.order

    if item.item_status != "RETURN_REQUESTED":
        return

    old_total = order.total_amount

    # restore stock
    if item.variant:
        item.variant.stock += item.quantity
        item.variant.save()

    item.item_status = "RETURNED"
    item.save()

    order.recalculate_totals()

    refund_amount = old_total - order.total_amount

    if refund_amount > 0 and order.is_paid:
        RefundService.refund_to_wallet(
            user=order.user,
            amount=refund_amount,
            order=order,
            source="RETURN_REFUND"
        )