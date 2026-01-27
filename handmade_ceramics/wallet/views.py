
from django.shortcuts import render, get_object_or_404, redirect
from wallet.models import Wallet, WalletTransaction
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from orders.models import Order
from django.contrib import messages
from cart.models import CartItem

@login_required
@transaction.atomic
def wallet_payment(request, order_id):
    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user,
        is_paid=False,
        status='PENDING'
    )

    wallet = Wallet.objects.select_for_update().get(user=request.user)

    # Prevent paying cancelled or zero-amount orders
    if order.status == 'CANCELLED':
        messages.error(request, "This order was cancelled.")
        return redirect("checkout:checkout")

    if order.total_amount <= 0:
        messages.error(request, "Invalid order amount.")
        return redirect(order.get_absolute_url())

    if wallet.balance < order.total_amount:
        messages.error(request, "Insufficient wallet balance.")
        return redirect(order.get_absolute_url())

    # Deduct money
    wallet.balance -= order.total_amount
    wallet.save()

    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type='DEBIT',
        amount=order.total_amount,
        description=f"Payment for order {order.order_id}"
    )

    # Mark order paid
    order.is_paid = True
    order.payment_method = 'WALLET'
    order.status = 'CONFIRMED'
    order.save()

    # Reduce stock
    for item in order.items.select_related('variant'):
        item.variant.stock -= item.quantity
        item.variant.save()

    CartItem.objects.filter(cart__user=request.user).delete()

    messages.success(request, "Order paid using wallet.")
    return redirect('payments:success')

@login_required
def wallet_dashboard(request):
    """
    Show user's wallet balance and transaction history.
    """
    wallet = Wallet.objects.get(user=request.user)
    transactions = wallet.transactions.order_by('-created_at')  # latest first

    context = {
        'wallet': wallet,
        'transactions': transactions,
    }
    return render(request, 'wallet/dashboard.html', context)
