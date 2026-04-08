# wallet/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages

from wallet.models import Wallet, WalletTransaction
from orders.models import Order
from cart.models import CartItem
from profiles.models import Profile


@login_required
@transaction.atomic
def wallet_payment(request, order_id):
    order = get_object_or_404(
        Order.objects.select_for_update(),
        order_id=order_id,
        user=request.user,
    )

    if order.is_paid:
        messages.error(request, "This order is already paid.")
        return redirect(order.get_absolute_url())

    if order.status not in ['PENDING']:
        messages.error(request, "This order cannot be paid.")
        return redirect(order.get_absolute_url())

    if order.total_amount <= 0:
        messages.error(request, "Invalid order amount.")
        return redirect(order.get_absolute_url())

    wallet, _ = Wallet.objects.select_for_update().get_or_create(
        user=request.user,
        defaults={'balance': 0}
    )

    if wallet.balance < order.total_amount:
        messages.error(request, "Insufficient wallet balance.")
        return redirect(order.get_absolute_url())

    wallet.balance -= order.total_amount
    wallet.save()

    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type=WalletTransaction.DEBIT,
        amount=order.total_amount,
        description=f"Payment for order {order.order_id}"
    )

    for item in order.items.select_related('variant'):

        if item.variant:
            if item.variant.stock < item.quantity:
                raise Exception(
                    f"Insufficient stock for {item.product_name}"
                )

            item.variant.stock -= item.quantity
            item.variant.save()

    order.is_paid = True
    order.payment_method = 'WALLET'
    order.status = 'CONFIRMED'
    order.save()

    CartItem.objects.filter(cart__user=request.user).delete()

    messages.success(request, "Order paid successfully using wallet.")

    return redirect('payments:success')


@login_required
def wallet_dashboard(request):

    wallet, _ = Wallet.objects.get_or_create(
        user=request.user,
        defaults={'balance': 0}
    )

    transactions = wallet.transactions.order_by('-created_at')

    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        profile = None
        
    context = {
        'wallet': wallet,
        'transactions': transactions,
        'profile': profile
    }

    return render(request, 'wallet/dashboard.html', context)