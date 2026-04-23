from django.db import transaction
from orders.models import OrderItem
from .refund_service import RefundService

from wallet.models import Wallet, WalletTransaction
class OrderService:

    @staticmethod
    @transaction.atomic
    def cancel_item(item):

        if item.item_status == 'CANCELLED':
            return

        order = item.order

        item.cancel_item()  

        item.refresh_from_db()

        if order.is_paid:

            refund_amount = item.final_total

            wallet, _ = Wallet.objects.get_or_create(user=order.user)

            wallet.balance += refund_amount
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=WalletTransaction.CREDIT,
                amount=refund_amount,
                description=f"Refund for cancelled item {item.product_name} ({order.order_id})"
            )


    @staticmethod
    @transaction.atomic
    def cancel_order(order):
        if order.status in ["CANCELLED", "RETURNED"]:
            return

        old_total = order.total_amount
        
        for item in order.items.all():
            if item.item_status not in ["CANCELLED", "RETURNED"]:
                if item.variant:
                    item.variant.stock += item.quantity
                    item.variant.save()
                item.item_status = "CANCELLED"
                item.save()

        order.status = "CANCELLED"
        order.recalculate_totals()

        refund_amount = order.calculate_refund(old_total)

        if order.is_paid and refund_amount > 0:
            RefundService.refund_to_wallet(
                user=order.user,
                amount=refund_amount,
                order=order,
                source="CANCEL_REFUND"
            )
        
        order.is_refunded = True
        order.save()

        from coupons.models import CouponUsage
        if order.coupon:
            CouponUsage.objects.filter(
                user=order.user,
                coupon=order.coupon,
                order=order
            ).delete()

    @staticmethod
    @transaction.atomic
    def process_item_return(item):

        if item.item_status != 'RETURN_REQUESTED':
            return

        order = item.order

        item.process_return()  # updates totals

        # 🔥 refresh after recalculation
        item.refresh_from_db()

        if order.is_paid:

            refund_amount = item.final_total

            wallet, _ = Wallet.objects.get_or_create(user=order.user)

            wallet.balance += refund_amount
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=WalletTransaction.CREDIT,
                amount=refund_amount,
                description=f"Refund for returned item {item.product_name} ({order.order_id})"
            )