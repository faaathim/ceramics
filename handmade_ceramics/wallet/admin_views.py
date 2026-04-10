# wallet/admin_views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q

from .models import WalletTransaction


def superuser_check(user):
    return user.is_active and user.is_superuser


@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def admin_wallet_transaction_list(request):

    transactions = WalletTransaction.objects.select_related(
        'wallet__user', 'order'
    ).all()

    q = request.GET.get('q', '').strip()
    if q:
        transactions = transactions.filter(
            Q(transaction_id__icontains=q) |
            Q(wallet__user__email__icontains=q)
        )

    transaction_type = request.GET.get('type')
    if transaction_type and transaction_type != "":
        transactions = transactions.filter(transaction_type=transaction_type)

    source = request.GET.get('source')
    if source and source != "":
        transactions = transactions.filter(source=source)

    paginator = Paginator(transactions.order_by('-created_at'), 10)
    page = request.GET.get('page')
    transaction_page = paginator.get_page(page)

    context = {
        'transactions': transaction_page,
        'q': q
    }

    return render(request, 'wallet/admin_transaction_list.html', context)


@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def admin_wallet_transaction_detail(request, transaction_id):
    transaction = get_object_or_404(
        WalletTransaction.objects.select_related(
            'wallet__user', 'order'
        ),
        transaction_id=transaction_id
    )

    context = {
        'transaction': transaction,
        'wallet': transaction.wallet,
        'user': transaction.wallet.user,
    }

    return render(request, 'wallet/admin_transaction_detail.html', context)