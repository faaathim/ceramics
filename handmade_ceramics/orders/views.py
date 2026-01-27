from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator
from .models import Order, OrderItem
from cart.models import CartItem
from user_profile.models import Profile
import io
from reportlab.pdfgen import canvas # type: ignore
from coupons.models import CouponUsage
from wallet.models import Wallet, WalletTransaction
from django.db import transaction



@login_required
def order_list(request):
    # Get user profile for sidebar
    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    # Get search query and status filter
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'all')
    
    # Filter orders
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    if query:
        orders = orders.filter(order_id__icontains=query)
    
    if status_filter and status_filter != 'all':
        orders = orders.filter(status=status_filter)
    
    # Pagination (optional)
    paginator = Paginator(orders, 10)  # 10 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'orders': page_obj,
        'profile': profile,
        'query': query,
        'status_filter': status_filter,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
    }
    
    return render(request, 'orders/order_list.html', context)


@login_required
def order_detail(request, order_id):
    # Get user profile for sidebar
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
@transaction.atomic
def cancel_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    if order.status not in ['PENDING', 'CONFIRMED']:
        messages.error(request, "Order cannot be cancelled.")
        return redirect(order.get_absolute_url())

    order.status = 'CANCELLED'
    order.save()

    # Refund to wallet if paid
    if order.is_paid:
        wallet = Wallet.objects.select_for_update().get(user=request.user)

        wallet.balance += order.total_amount
        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='CREDIT',
            amount=order.total_amount,
            description=f"Refund for cancelled order {order.order_id}"
        )

    messages.success(request, "Order cancelled and amount refunded to wallet.")
    return redirect(order.get_absolute_url())



@login_required
@transaction.atomic
def return_order(request, order_id):
    # Get user profile for sidebar
    profile, _ = Profile.objects.get_or_create(user=request.user)

    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    # Only delivered orders can be returned
    if order.status != 'DELIVERED':
        messages.error(request, 'Only delivered orders can be returned.')
        return redirect('orders:order_list')

    if request.method == 'POST':
        reason = request.POST.get('reason', '')

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
            f'Return request for order {order.order_id} has been submitted successfully.'
        )
        return redirect('orders:order_list')

    return render(request, 'orders/order_return_form.html', {
        'order': order,
        'profile': profile
    })


@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)

    # Starting position
    x_margin = 50
    y = 800

    # ------------------------
    # Store / Invoice Header
    # ------------------------
    p.setFont("Helvetica-Bold", 18)
    p.drawString(x_margin, y, "Handmade Ceramics Store")

    y -= 25
    p.setFont("Helvetica", 10)
    p.drawString(x_margin, y, "Handcrafted ceramic products made with love")
    y -= 15
    p.drawString(x_margin, y, "Email: support@ceramics.com | Phone: +91-XXXXXXXXXX")

    # Invoice title
    p.setFont("Helvetica-Bold", 16)
    p.drawRightString(550, 800, "INVOICE")

    # ------------------------
    # Order Details
    # ------------------------
    y -= 40
    p.setFont("Helvetica", 11)
    p.drawString(x_margin, y, f"Order ID: {order.order_id}")
    y -= 15
    p.drawString(x_margin, y, f"Order Date: {order.created_at.strftime('%d %B %Y')}")
    y -= 15
    p.drawString(x_margin, y, f"Order Status: {order.get_status_display()}")

    # ------------------------
    # Customer Details
    # ------------------------
    y -= 30
    p.setFont("Helvetica-Bold", 12)
    p.drawString(x_margin, y, "Billing Address")

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
    y -= 15
    p.drawString(x_margin, y, f"Phone: {order.shipping_phone}")
    y -= 15
    p.drawString(x_margin, y, f"Email: {order.shipping_email}")

    # ------------------------
    # Order Items Header
    # ------------------------
    y -= 35
    p.setFont("Helvetica-Bold", 12)
    p.drawString(x_margin, y, "Order Items")

    y -= 10
    p.line(x_margin, y, 550, y)

    # ------------------------
    # Order Items List
    # ------------------------
    y -= 20
    p.setFont("Helvetica", 11)

    for item in order.items.all():
        # Page break if space is low
        if y < 100:
            p.showPage()
            y = 800
            p.setFont("Helvetica", 11)

        item_name = item.product_name
        if item.variant_color:
            item_name += f" ({item.variant_color})"

        p.drawString(x_margin, y, item_name)
        y -= 15

        p.drawString(
            x_margin + 20,
            y,
            f"Qty: {item.quantity}  |  Price: {item.unit_price:.2f}  |  Total: {item.item_total:.2f}"
        )
        y -= 20

    # ------------------------
    # Total Amount
    # ------------------------
    y -= 10
    p.line(x_margin, y, 550, y)

    y -= 25
    p.setFont("Helvetica-Bold", 13)
    p.drawRightString(550, y, f"Total Amount: {order.total_amount:.2f}")

    # ------------------------
    # Footer
    # ------------------------
    p.setFont("Helvetica", 9)
    p.drawString(x_margin, 50, "This is a system generated invoice.")
    p.drawRightString(550, 50, "Thank you for shopping with us!")

    p.showPage()
    p.save()

    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="invoice_{order.order_id}.pdf"'
    )
    return response
