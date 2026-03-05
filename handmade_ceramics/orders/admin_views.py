# orders/admin_views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db import transaction

from .models import Order, OrderItem
from product_management.models import Variant
from wallet.models import Wallet, WalletTransaction

def superuser_check(user):
    return user.is_active and user.is_superuser


# admin order list
@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def admin_order_list(request):
    orders = Order.objects.select_related('user').all()

    q = request.GET.get('q', '').strip()
    if q:
        orders = orders.filter(
            Q(order_id__icontains=q) |
            Q(user__email__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q)
        )

    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if date_from:
        try:
            dt_from = timezone.datetime.fromisoformat(date_from)
            orders = orders.filter(created_at__date__gte=dt_from.date())
        except ValueError:
            pass

    if date_to:
        try:
            dt_to = timezone.datetime.fromisoformat(date_to)
            orders = orders.filter(created_at__date__lte=dt_to.date())
        except ValueError:
            pass

    sort = request.GET.get('sort', '-created_at')
    allowed_sorts = ['created_at', '-created_at', 'total_amount', '-total_amount']

    if sort not in allowed_sorts:
        sort = '-created_at'

    orders = orders.order_by(sort)

    paginator = Paginator(orders, 10)
    page = request.GET.get('page', 1)

    try:
        orders_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        orders_page = paginator.page(1)

    query_params = request.GET.copy()
    query_params.pop('page', None)

    context = {
        'orders': orders_page,
        'paginator': paginator,
        'query_params': query_params.urlencode(),
        'q': q,
        'status': status,
        'status_choices': Order._meta.get_field('status').choices,
        'date_from': date_from,
        'date_to': date_to,
        'sort': sort,
    }

    return render(request, 'orders/admin_order_list.html', context)


@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
@transaction.atomic
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    items = order.items.select_related('variant', 'product')

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if not order.can_change_status(new_status):
            messages.error(
                request,
                f"Invalid status change from "
                f"{order.get_status_display()} to "
                f"{new_status.replace('_', ' ').title()}."
            )
            return redirect(
                reverse('custom_admin:orders_admin:admin_order_detail',
                        args=[order.order_id])
            )

        old_status = order.status
        order.status = new_status

        # ✅ If order is delivered → update items
        if new_status == 'DELIVERED':
            # Mark COD as paid
            if order.payment_method == 'COD':
                order.is_paid = True

            # ✅ Update only active items
            order.items.exclude(item_status__in=['CANCELLED', 'RETURNED']).update(item_status='DELIVERED')

            # ✅ Recalculate totals (optional but safe)
            order.recalculate_totals()


        # 🔥 When admin marks RETURN_PROCESSING
        if new_status == 'RETURN_PROCESSING':
            order.items.update(item_status='RETURN_PROCESSING')


        # 🔥 When admin marks RETURNED
        if new_status == 'RETURNED':

            # 1️⃣ Increase stock back
            for item in order.items.select_related('variant'):
                if item.variant:
                    item.variant.stock += item.quantity
                    item.variant.save()

            # 2️⃣ Update all items to RETURNED
            order.items.update(item_status='RETURNED')

            # 3️⃣ Refund if eligible and not already refunded
            if (order.is_paid or order.payment_method == 'COD') and not order.is_refunded:

                wallet, _ = Wallet.objects.select_for_update().get_or_create(
                    user=order.user,
                    defaults={'balance': 0}
                )

                wallet.balance += order.total_amount
                wallet.save()

                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type=WalletTransaction.CREDIT,
                    source='RETURN_REFUND',
                    amount=order.total_amount,
                    description=f"Refund for returned order {order.order_id}",
                    order=order
                )

                order.is_refunded = True

        order.save()

        messages.success(
            request,
            f"Order status updated to {order.get_status_display()}."
        )

        return redirect(
            reverse('custom_admin:orders_admin:admin_order_detail',
                    args=[order.order_id])
        )

    context = {
        'order': order,
        'items': items,
        'status_choices': Order._meta.get_field('status').choices,
    }

    return render(request, 'orders/admin_order_detail.html', context)


# admin inventory
@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def admin_inventory(request):

    variants = Variant.objects.select_related('product').order_by('-updated_at')

    paginator = Paginator(variants, 25)
    page = request.GET.get('page', 1)

    try:
        variants_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        variants_page = paginator.page(1)

    context = {
        'variants': variants_page,
    }

    return render(request, 'orders/admin_inventory.html', context)


@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
@transaction.atomic
def admin_verify_return(request, order_id):

    order = get_object_or_404(Order, order_id=order_id)

    if order.status != 'RETURN_REQUESTED':
        messages.error(request, "No return request found.")
        return redirect('custom_admin:orders_admin:admin_order_detail', order_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        # ✅ APPROVE
        if action == 'approve':
            order.status = 'RETURN_PROCESSING'
            order.items.update(item_status='RETURN_PROCESSING')
            order.save()

            messages.success(request, "Return approved.")

        # ❌ REJECT
        elif action == 'reject':
            rejection_reason = request.POST.get('reason', '').strip()

            order.status = 'DELIVERED'
            order.return_rejection_reason = rejection_reason
            order.save()

            # Restore items to delivered
            order.items.update(item_status='DELIVERED')

            messages.success(request, "Return rejected.")

    return redirect('custom_admin:orders_admin:admin_order_detail', order_id)


@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
@transaction.atomic
def admin_complete_return(request, order_id):

    order = get_object_or_404(Order, order_id=order_id)

    if order.status != 'RETURN_PROCESSING':
        messages.error(request, "Return not in processing state.")
        return redirect('custom_admin:orders_admin:admin_order_detail', order_id)

    # 1️⃣ Restore stock
    for item in order.items.select_related('variant'):
        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save()

        item.item_status = 'RETURNED'
        item.save()

    # 2️⃣ Refund wallet
    if (order.is_paid or order.payment_method == 'COD') and not order.is_refunded:

        wallet, _ = Wallet.objects.select_for_update().get_or_create(
            user=order.user,
            defaults={'balance': 0}
        )

        wallet.balance += order.total_amount
        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransaction.CREDIT,
            source='RETURN_REFUND',
            amount=order.total_amount,
            description=f"Refund for returned order {order.order_id}",
            order=order
        )

        order.is_refunded = True

    order.status = 'RETURNED'
    order.save()

    messages.success(request, "Return completed and refund processed.")

    return redirect('custom_admin:orders_admin:admin_order_detail', order_id)