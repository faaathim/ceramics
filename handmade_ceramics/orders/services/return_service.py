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

        refund_total = 0

        items = order.items.filter(item_status="RETURN_PROCESSING")

        for item in items:

            # restore stock
            if item.variant:
                item.variant.stock = F("stock") + item.quantity
                item.variant.save()

            refund_total += item.item_total

            item.item_status = "RETURNED"
            item.save()

        # refund wallet
        if (order.is_paid or order.payment_method == "COD"):

            wallet, _ = Wallet.objects.select_for_update().get_or_create(
                user=order.user,
                defaults={"balance": 0}
            )

            wallet.balance = F("balance") + refund_total
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type="CREDIT",
                source="RETURN_REFUND",
                amount=refund_total,
                description=f"Refund for returned order {order.order_id}",
                order=order
            )

        order.status = "RETURNED"
        order.save()

        return True