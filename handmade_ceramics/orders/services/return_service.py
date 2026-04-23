from django.db import transaction
from django.db.models import F

from wallet.models import Wallet, WalletTransaction
from orders.models import OrderItem


class ReturnService:

    @staticmethod
    @transaction.atomic
    def approve_order_return(order):
        """
        Admin approves a full order return
        """

        if order.status != "RETURN_REQUESTED" and order.status != "PARTIAL_RETURN_REQUESTED":
            print(f"status:{order.status}")
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
        """
        Admin rejects a return request
        """

        if order.status not in ["RETURN_REQUESTED", "PARTIAL_RETURN_REQUESTED"]:
            return False

        order.status = "DELIVERED"
        order.return_rejection_reason = reason
        order.save()

        order.items.filter(
            item_status="RETURN_REQUESTED"
        ).update(item_status="DELIVERED")

        return True


    @staticmethod
    @transaction.atomic
    def complete_order_return(order):
        """
        Admin completes the return
        """
        if order.status != "RETURN_PROCESSING" and order.status != "PARTIAL_RETURN_REQUESTED":
            return False

        # We use a loop to process each item that is being returned
        # This allows us to handle partial returns correctly
        items_to_process = order.items.filter(item_status__in=["RETURN_REQUESTED", "RETURN_PROCESSING"])
        
        from .order_service import OrderService
        for item in items_to_process:
            OrderService.process_item_return(item)

        order.status = "RETURNED"
        order.save()

        return True