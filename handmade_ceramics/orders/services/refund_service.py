from django.db import transaction
from django.db.models import F
from wallet.models import Wallet, WalletTransaction


class RefundService:

    @staticmethod
    @transaction.atomic
    def refund_to_wallet(user, amount, order, source):

        if amount <= 0:
            return

        wallet, _ = Wallet.objects.select_for_update().get_or_create(
            user=user,
            defaults={"balance": 0}
        )

        wallet.balance = F("balance") + amount
        wallet.save()
        wallet.refresh_from_db()

        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransaction.CREDIT,
            source=source,
            amount=amount,
            description=f"Refund for order {order.order_id}",
            order=order
        )