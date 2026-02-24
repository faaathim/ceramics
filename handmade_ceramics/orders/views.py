# orders/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.utils import timezone

from .models import Order
from cart.models import CartItem
from user_profile.models import Profile
from coupons.models import CouponUsage
from wallet.models import Wallet, WalletTransaction

import io
from reportlab.pdfgen import canvas  # type: ignore


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

    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user
    )

    items = order.items.all()

    context = {
        "order": order,
        "items": items,
        "profile": profile,
    }

    return render(request, "orders/order_detail.html", context)


@login_required
@transaction.atomic
def cancel_order(request, order_id):
    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user
    )

    if order.status not in ['PENDING', 'CONFIRMED']:
        messages.error(request, "Order cannot be cancelled.")
        return redirect(order.get_absolute_url())

    order.status = 'CANCELLED'
    order.save()

    if order.is_paid and not order.is_refunded:

        wallet, _ = Wallet.objects.select_for_update().get_or_create(
            user=request.user,
            defaults={'balance': 0}
        )

        wallet.balance += order.total_amount
        wallet.save()

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

    messages.success(
        request,
        "Order cancelled successfully. Refund processed if applicable."
    )

    return redirect(order.get_absolute_url())


@login_required
@transaction.atomic
def return_order(request, order_id):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user
    )

    if order.status != 'DELIVERED':
        messages.error(request, 'Only delivered orders can be returned.')
        return redirect('orders:order_list')

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()

        if not reason:
            messages.error(request, 'Please provide a return reason.')
            return render(request, 'orders/order_return_form.html', {
                'order': order,
                'profile': profile
            })

        order.status = 'RETURN_REQUESTED'
        order.return_reason = reason
        order.save()

        messages.success(
            request,
            f'Return request for order {order.order_id} submitted successfully.'
        )

        return redirect('orders:order_list')

    return render(request, 'orders/order_return_form.html', {
        'order': order,
        'profile': profile
    })


@login_required
def download_invoice(request, order_id):
    """
    Generates PDF invoice for the order
    """

    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user
    )

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)

    x_margin = 50
    y = 800

    p.setFont("Helvetica-Bold", 18)
    p.drawString(x_margin, y, "Handmade Ceramics Store")

    y -= 25
    p.setFont("Helvetica", 10)
    p.drawString(x_margin, y, "Handcrafted ceramic products made with love")
    y -= 15
    p.drawString(x_margin, y, "Email: support@ceramics.com")

    p.setFont("Helvetica-Bold", 16)
    p.drawRightString(550, 800, "INVOICE")

    y -= 40
    p.setFont("Helvetica", 11)
    p.drawString(x_margin, y, f"Order ID: {order.order_id}")
    y -= 15
    p.drawString(
        x_margin,
        y,
        f"Order Date: {order.created_at.strftime('%d %B %Y')}"
    )
    y -= 15
    p.drawString(x_margin, y, f"Status: {order.get_status_display()}")

    y -= 30
    p.setFont("Helvetica-Bold", 12)
    p.drawString(x_margin, y, "Shipping Address")

    y -= 18
    p.setFont("Helvetica", 11)
    p.drawString(x_margin, y, order.shipping_full_name)
    y -= 15
    p.drawString(x_margin, y, order.shipping_address_line)
    y -= 15
    p.drawString(
        x_margin,
        y,
        f"{order.shipping_city}, {order.shipping_state} - {order.shipping_pincode}"
    )

    y -= 35
    p.setFont("Helvetica-Bold", 12)
    p.drawString(x_margin, y, "Order Items")
    y -= 15

    p.setFont("Helvetica", 11)

    for item in order.items.all():

        if y < 100:
            p.showPage()
            y = 800
            p.setFont("Helvetica", 11)

        name = item.product_name
        if item.variant_color:
            name += f" ({item.variant_color})"

        p.drawString(x_margin, y, name)
        y -= 15

        p.drawString(
            x_margin + 20,
            y,
            f"Qty: {item.quantity} | "
            f"Price: {item.unit_price:.2f} | "
            f"Total: {item.item_total:.2f}"
        )
        y -= 20

    y -= 10
    p.line(x_margin, y, 550, y)

    y -= 25
    p.setFont("Helvetica-Bold", 13)
    p.drawRightString(550, y, f"Total Amount: {order.total_amount:.2f}")

    p.setFont("Helvetica", 9)
    p.drawString(x_margin, 50, "System generated invoice.")
    p.drawRightString(550, 50, "Thank you for shopping!")

    p.showPage()
    p.save()

    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="invoice_{order.order_id}.pdf"'
    )

    return response