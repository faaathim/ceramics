from django.db import transaction
from .models import WalletTransaction

@transaction.atomic
def credit_wallet(wallet, amount, description, order=None):
    wallet.balance += amount
    wallet.save(update_fields=['balance'])

    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type=WalletTransaction.CREDIT,
        amount=amount,
        description=description,
        order=order
    )


@transaction.atomic
def debit_wallet(wallet, amount, description, order=None):
    if wallet.balance < amount:
        raise ValueError("Insufficient wallet balance")

    wallet.balance -= amount
    wallet.save(update_fields=['balance'])

    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type=WalletTransaction.DEBIT,
        amount=amount,
        description=description,
        order=order
    )
