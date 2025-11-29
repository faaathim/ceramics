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
    # Get user profile for sidebar
    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    # Check if order can be cancelled
    if order.status in ['CANCELLED', 'DELIVERED', 'RETURNED']:
        messages.error(request, 'This order cannot be cancelled.')
        return redirect('orders:order_list')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        if not reason:
            messages.error(request, 'Please provide a cancellation reason.')
            return render(request, 'orders/order_cancel_form.html', {
                'order': order,
                'profile': profile
            })
        
        order.status = 'CANCELLED'
        order.cancellation_reason = reason
        order.save()
        
        # Return stock for all items
        for item in order.items.all():
            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save()
        
        messages.success(request, f'Order {order.order_id} has been cancelled successfully.')
        return redirect('orders:order_list')
    
    return render(request, 'orders/order_cancel_form.html', {
        'order': order,
        'profile': profile
    })


@login_required
@transaction.atomic
def return_order(request, order_id):
    # Get user profile for sidebar
    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    if order.status != 'DELIVERED':
        messages.error(request, 'Only delivered orders can be returned.')
        return redirect('orders:order_list')
    
    if order.status == 'RETURNED':
        messages.error(request, 'This order has already been returned.')
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
        
        messages.success(request, f'Return request for order {order.order_id} has been submitted successfully.')
        return redirect('orders:order_list')
    
    return render(request, 'orders/order_return_form.html', {
        'order': order,
        'profile': profile
    })


@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    # Create PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    
    # Header
    p.setFont("Helvetica-Bold", 20)
    p.drawString(100, 800, "INVOICE")
    
    # Order Details
    p.setFont("Helvetica", 12)
    p.drawString(100, 770, f"Order ID: {order.order_id}")
    p.drawString(100, 750, f"Date: {order.created_at.strftime('%B %d, %Y')}")
    p.drawString(100, 730, f"Status: {order.get_status_display()}")
    
    # Customer Details
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 700, "Customer Information:")
    p.setFont("Helvetica", 12)
    p.drawString(100, 680, f"Name: {order.shipping_full_name}")
    p.drawString(100, 660, f"Email: {order.user.email}")
    p.drawString(100, 640, f"Phone: {order.shipping_phone}")
    p.drawString(100, 620, f"Address: {order.shipping_address}")
    p.drawString(100, 600, f"{order.shipping_city}, {order.shipping_state} - {order.shipping_pincode}")
    
    # Items Header
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 570, "Order Items:")
    
    # Items Table
    p.setFont("Helvetica", 11)
    y = 550
    for item in order.items.all():
        item_text = f"{item.product_name}"
        if item.variant_color:
            item_text += f" ({item.variant_color})"
        item_text += f" x {item.quantity} = ₹{item.item_total}"
        p.drawString(100, y, item_text)
        y -= 20
    
    # Total
    y -= 20
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y, f"Total Amount: ₹{order.total_amount}")
    
    # Footer
    p.setFont("Helvetica", 10)
    p.drawString(100, 50, "Thank you for your order!")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    
    # Return PDF response
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_id}.pdf"'
    
    return response