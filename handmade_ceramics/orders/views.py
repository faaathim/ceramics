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
from decimal import Decimal
from .models import Order, OrderItem
from profiles.models import Profile
from coupons.models import CouponUsage
from wallet.models import Wallet, WalletTransaction
from orders.services.order_service import OrderService
from django.db.models import Sum

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
    refunded_amount = order.items.filter(item_status='RETURNED').aggregate(total=Sum('final_total'))['total'] or Decimal('0.00')

    return render(request, "orders/order_detail.html", {
        "order": order,
        "items": items,
        "profile": profile,
        "refunded_amount": refunded_amount,
    })

@login_required
@require_POST
@transaction.atomic
def cancel_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    if order.status not in ['PENDING', 'CONFIRMED']:
        messages.error(request, "Order cannot be cancelled.")
        return redirect(order.get_absolute_url())

    OrderService.cancel_order(order)

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


def download_invoice(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    items = order.items.all()

    for item in items:
        item.item_total = item.unit_price * item.quantity

    subtotal = getattr(order, 'subtotal', None) or sum(item.item_total for item in items)
    discount = getattr(order, 'discount_amount', 0) or 0
    tax      = getattr(order, 'tax_amount',      0) or 0
    shipping = getattr(order, 'shipping_charge', 0) or 0
    total    = getattr(order, 'total_amount', subtotal - discount + tax + shipping)

    html = render_to_string("orders/invoice.html", {
        "order":    order,
        "items":    items,
        "subtotal": subtotal,
        "discount": discount,
        "tax":      tax,
        "shipping": shipping,
        "total":    total,
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{order.order_id}.pdf"'
    weasyprint.HTML(string=html).write_pdf(response)
    return response
