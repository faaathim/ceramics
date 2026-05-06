from django.db import transaction
from orders.services.refund_service import RefundService


class OrderItemService:

    @staticmethod
    @transaction.atomic
    def process_return(order_item):

        if order_item.item_status != 'RETURN_REQUESTED':
            return

        if order_item.variant:
            order_item.variant.stock += order_item.quantity
            order_item.variant.save()

        RefundService.refund_to_wallet(
            user=order_item.order.user,
            amount=order_item.final_total,
            order=order_item.order,
            source='RETURN_REFUND'
        )

        order_item.item_status = 'RETURNED'
        order_item.save()

        order_item.order.recalculate_totals()