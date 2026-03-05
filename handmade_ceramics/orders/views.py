# orders/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.db.models import F
from django.views.decorators.http import require_POST
import weasyprint

from .models import Order, OrderItem
from user_profile.models import Profile
from coupons.models import CouponUsage
from wallet.models import Wallet, WalletTransaction


@login_required
def order_list(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'all')

    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    if query:
        orders = orders.filter(order_id__icontains=query)

    if status_filter != 'all':
        orders = orders.filter(status=status_filter)

    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'orders': page_obj,
        'profile': profile,
        'query': query,
        'status_filter': status_filter,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
    }

    return render(request, 'orders/order_list.html', context)


@login_required
def order_detail(request, order_id):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    items = order.items.all()

    context = {
        "order": order,
        "items": items,
        "profile": profile,
    }

    return render(request, "orders/order_detail.html", context)


@login_required
@require_POST
@transaction.atomic
def cancel_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    if order.status not in ['PENDING', 'CONFIRMED']:
        messages.error(request, "Order cannot be cancelled.")
        return redirect(order.get_absolute_url())

    # Cancel all items and restore stock
    for item in order.items.all():
        if item.item_status not in ['CANCELLED', 'RETURNED']:
            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save()
            item.item_status = 'CANCELLED'
            item.save()

    order.status = 'CANCELLED'
    order.save()

    # Refund if paid
    if order.is_paid and not order.is_refunded:
        wallet, _ = Wallet.objects.select_for_update().get_or_create(
            user=request.user,
            defaults={'balance': 0}
        )
        wallet.balance = F('balance') + order.total_amount
        wallet.save()
        wallet.refresh_from_db()

        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransaction.CREDIT,
            source='CANCEL_REFUND',
            amount=order.total_amount,
            description=f"Refund for cancelled order {order.order_id}",
            order=order
        )
        order.is_refunded = True
        order.save()

    # Remove coupon usage
    if order.coupon:
        CouponUsage.objects.filter(
            user=request.user,
            coupon=order.coupon,
            order=order
        ).delete()

    messages.success(request, "Order cancelled successfully. Refund processed if applicable.")
    return redirect(order.get_absolute_url())


@login_required
@require_POST
@transaction.atomic
def cancel_order_item(request, order_id, item_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    item = get_object_or_404(OrderItem, id=item_id, order=order)

    if item.item_status not in ['PENDING', 'CONFIRMED']:
        messages.error(request, "Item cannot be cancelled.")
        return redirect('orders:order_detail', order_id=order_id)

    old_total = order.total_amount
    item.cancel_item()

    order.refresh_from_db()
    new_total = order.total_amount
    refund_amount = old_total - new_total

    if order.is_paid and refund_amount > 0:
        wallet, _ = Wallet.objects.select_for_update().get_or_create(
            user=request.user,
            defaults={'balance': 0}
        )
        wallet.balance = F('balance') + refund_amount
        wallet.save()
        wallet.refresh_from_db()

        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransaction.CREDIT,
            source='CANCEL_REFUND',
            amount=refund_amount,
            description=f"Refund for cancelled item in order {order.order_id}",
            order=order
        )

    # If all items cancelled → mark order cancelled
    if not order.items.exclude(item_status='CANCELLED').exists():
        order.status = 'CANCELLED'
        order.save()

        if order.coupon:
            CouponUsage.objects.filter(
                user=request.user,
                coupon=order.coupon,
                order=order
            ).delete()

    messages.success(request, "Item cancelled successfully. Refund processed if applicable.")
    return redirect('orders:order_detail', order_id=order_id)


@login_required
@require_POST
@transaction.atomic
def return_order(request, order_id):

    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    if order.status != 'DELIVERED':
        messages.error(request, "Order not eligible for return.")
        return redirect('orders:order_detail', order_id=order_id)

    reason = request.POST.get('reason', '').strip()

    if not reason:
        messages.error(request, "Please provide return reason.")
        return redirect('orders:order_detail', order_id=order_id)

    # Mark full order return requested
    order.status = 'RETURN_REQUESTED'
    order.return_reason = reason
    order.save()

    # Mark all items
    order.items.update(
        item_status='RETURN_REQUESTED',
        return_reason=reason
    )

    messages.success(request, "Return request submitted successfully.")
    return redirect('orders:order_detail', order_id=order_id)
# orders/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.db.models import F
from django.views.decorators.http import require_POST
import weasyprint

from .models import Order, OrderItem
from user_profile.models import Profile
from coupons.models import CouponUsage
from wallet.models import Wallet, WalletTransaction


@login_required
def order_list(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'all')

    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    if query:
        orders = orders.filter(order_id__icontains=query)

    if status_filter != 'all':
        orders = orders.filter(status=status_filter)

    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'orders': page_obj,
        'profile': profile,
        'query': query,
        'status_filter': status_filter,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
    }

    return render(request, 'orders/order_list.html', context)


@login_required
def order_detail(request, order_id):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    items = order.items.all()

    context = {
        "order": order,
        "items": items,
        "profile": profile,
    }

    return render(request, "orders/order_detail.html", context)


@login_required
@require_POST
@transaction.atomic
def cancel_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    if order.status not in ['PENDING', 'CONFIRMED']:
        messages.error(request, "Order cannot be cancelled.")
        return redirect(order.get_absolute_url())

    # Cancel all items and restore stock
    for item in order.items.all():
        if item.item_status not in ['CANCELLED', 'RETURNED']:
            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save()
            item.item_status = 'CANCELLED'
            item.save()

    order.status = 'CANCELLED'
    order.save()

    # Refund if paid
    if order.is_paid and not order.is_refunded:
        wallet, _ = Wallet.objects.select_for_update().get_or_create(
            user=request.user,
            defaults={'balance': 0}
        )
        wallet.balance = F('balance') + order.total_amount
        wallet.save()
        wallet.refresh_from_db()

        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransaction.CREDIT,
            source='CANCEL_REFUND',
            amount=order.total_amount,
            description=f"Refund for cancelled order {order.order_id}",
            order=order
        )
        order.is_refunded = True
        order.save()

    # Remove coupon usage
    if order.coupon:
        CouponUsage.objects.filter(
            user=request.user,
            coupon=order.coupon,
            order=order
        ).delete()

    messages.success(request, "Order cancelled successfully. Refund processed if applicable.")
    return redirect(order.get_absolute_url())


@login_required
@require_POST
@transaction.atomic
def cancel_order_item(request, order_id, item_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    item = get_object_or_404(OrderItem, id=item_id, order=order)

    if item.item_status not in ['PENDING', 'CONFIRMED']:
        messages.error(request, "Item cannot be cancelled.")
        return redirect('orders:order_detail', order_id=order_id)

    old_total = order.total_amount
    item.cancel_item()

    order.refresh_from_db()
    new_total = order.total_amount
    refund_amount = old_total - new_total

    if order.is_paid and refund_amount > 0:
        wallet, _ = Wallet.objects.select_for_update().get_or_create(
            user=request.user,
            defaults={'balance': 0}
        )
        wallet.balance = F('balance') + refund_amount
        wallet.save()
        wallet.refresh_from_db()

        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransaction.CREDIT,
            source='CANCEL_REFUND',
            amount=refund_amount,
            description=f"Refund for cancelled item in order {order.order_id}",
            order=order
        )

    # If all items cancelled → mark order cancelled
    if not order.items.exclude(item_status='CANCELLED').exists():
        order.status = 'CANCELLED'
        order.save()

        if order.coupon:
            CouponUsage.objects.filter(
                user=request.user,
                coupon=order.coupon,
                order=order
            ).delete()

    messages.success(request, "Item cancelled successfully. Refund processed if applicable.")
    return redirect('orders:order_detail', order_id=order_id)


@login_required
@require_POST
@transaction.atomic
def return_order(request, order_id):

    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    if order.status != 'DELIVERED':
        messages.error(request, "Order not eligible for return.")
        return redirect('orders:order_detail', order_id=order_id)

    reason = request.POST.get('reason', '').strip()

    if not reason:
        messages.error(request, "Please provide return reason.")
        return redirect('orders:order_detail', order_id=order_id)

    # Mark full order return requested
    order.status = 'RETURN_REQUESTED'
    order.return_reason = reason
    order.save()

    # Mark all items
    order.items.update(
        item_status='RETURN_REQUESTED',
        return_reason=reason
    )

    messages.success(request, "Return request submitted successfully.")
    return redirect('orders:order_detail', order_id=order_id)


@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    html = render_to_string("orders/invoice.html", {"order": order})

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{order.order_id}.pdf"'

    weasyprint.HTML(string=html).write_pdf(response)

    return response

@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    html = render_to_string("orders/invoice.html", {"order": order})

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{order.order_id}.pdf"'

    weasyprint.HTML(string=html).write_pdf(response)

    return response