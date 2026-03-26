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
from orders.services.order_service import OrderService

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

    return render(request, "orders/order_detail.html", {
        "order": order,
        "items": items,
        "profile": profile,
    })

@login_required
@require_POST
@transaction.atomic
def cancel_order(request, order_id):

    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    if order.status not in ['PENDING', 'CONFIRMED']:
        messages.error(request, "Order cannot be cancelled.")
        return redirect(order.get_absolute_url())

    for item in order.items.all():

        if item.item_status not in ['CANCELLED', 'RETURNED']:

            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save()

            item.item_status = 'CANCELLED'
            item.save()

    order.status = 'CANCELLED'
    order.save()

    if order.is_paid and not order.is_refunded and order.payment_method != "COD":

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

    if order.coupon:
        CouponUsage.objects.filter(
            user=request.user,
            coupon=order.coupon,
            order=order
        ).delete()

    messages.success(request, "Order cancelled successfully.")
    return redirect(order.get_absolute_url())

@login_required
@require_POST
def cancel_order_item(request, order_id, item_id):

    item = get_object_or_404(
        OrderItem,
        id=item_id,
        order__order_id=order_id,
        order__user=request.user
    )

    OrderService.cancel_item(item)

    messages.success(request, "Item cancelled successfully.")

    return redirect(item.order.get_absolute_url())


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

    # Only update delivered items
    delivered_items = order.items.filter(item_status='DELIVERED')

    if not delivered_items.exists():
        messages.error(request, "No delivered items available for return.")
        return redirect('orders:order_detail', order_id=order_id)

    delivered_items.update(
        item_status='RETURN_REQUESTED',
        return_reason=reason
    )

    order.status = 'RETURN_REQUESTED'
    order.return_reason = reason
    order.save()

    messages.success(request, "Return request submitted successfully.")
    return redirect('orders:order_detail', order_id=order_id)


@login_required
@require_POST
@transaction.atomic
def request_item_return(request, item_id):

    item = get_object_or_404(
        OrderItem,
        id=item_id,
        order__user=request.user
    )

    if item.item_status != 'DELIVERED':
        messages.error(request, "Item cannot be returned.")
        return redirect(item.order.get_absolute_url())

    reason = request.POST.get('reason', '')

    item.item_status = 'RETURN_REQUESTED'
    item.return_reason = reason
    item.save()

    order = item.order

    delivered_items = order.items.filter(item_status='DELIVERED')
    requested_items = order.items.filter(item_status='RETURN_REQUESTED')

    if delivered_items.count() == requested_items.count():
        order.status = 'RETURN_REQUESTED'
    else:
        order.status = 'PARTIAL_RETURN_REQUESTED'

    order.save()

    messages.success(request, "Return request submitted.")

    return redirect(order.get_absolute_url())


@login_required
def download_invoice(request, order_id):

    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    html = render_to_string("orders/invoice.html", {"order": order})

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{order.order_id}.pdf"'

    weasyprint.HTML(string=html).write_pdf(response)

    return response

