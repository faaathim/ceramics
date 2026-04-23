# cart/views.py

from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import HttpResponseBadRequest, JsonResponse
from django.urls import reverse

from .models import Cart, CartItem
from product_management.models import Variant

try:
    from wishlist.models import Wishlist
except ImportError:
    Wishlist = None

try:
    from coupons.models import Coupon
except Exception:
    Coupon = None


def _max_qty_limit():
    return getattr(settings, 'CART_MAX_QTY_PER_ITEM', 10)


def _get_user_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def add_to_cart(request):
    referer = request.META.get('HTTP_REFERER', reverse('cart:cart_page'))
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect(referer)

    try:
        variant_id = int(request.POST.get('variant_id'))
    except (TypeError, ValueError):
        messages.error(request, "Invalid variant id.")
        return redirect(referer)

    try:
        qty_requested = int(request.POST.get('qty', 1))
    except (TypeError, ValueError):
        qty_requested = 1

    if qty_requested < 1:
        qty_requested = 1

    variant = get_object_or_404(Variant, pk=variant_id)

    if variant.is_deleted or not variant.is_listed:
        messages.error(request, "This variant is not available.")
        return redirect(referer)

    product = variant.product
    if product.is_deleted or not product.is_listed:
        messages.error(request, "This product is not available.")
        return redirect(referer)

    category = getattr(product, 'category', None)
    if category and getattr(category, 'is_blocked', False):
        messages.error(request, "This category is blocked.")
        return redirect(referer)

    site_max = _max_qty_limit()
    allowed_max = min(site_max, variant.stock or 0)

    if allowed_max <= 0:
        messages.error(request, "This variant is out of stock.")
        return redirect(referer)

    qty_to_add = min(qty_requested, allowed_max)

    cart = _get_user_cart(request.user)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant
    )

    if created:
        cart_item.quantity = qty_to_add
        messages.success(request, f"Added {product.name} to your cart.")
    else:
        old_qty = cart_item.quantity
        new_qty = min(old_qty + qty_to_add, allowed_max)
        cart_item.quantity = new_qty
        
        if old_qty >= allowed_max:
            messages.warning(request, f"You already have the maximum allowed quantity ({allowed_max}) of {product.name} in your cart.")
        elif new_qty == allowed_max:
            messages.success(request, f"Added {product.name} to cart. You've reached the maximum limit of {allowed_max}.")
        else:
            messages.success(request, f"Updated {product.name} quantity in your cart.")

    cart_item.save()
    if Wishlist:
        Wishlist.objects.filter(
            user=request.user,
            variant=variant
        ).delete()

    return redirect(reverse('cart:cart_page'))



@login_required
def cart_page(request):
    cart = _get_user_cart(request.user)
    items = list(cart.items.select_related('variant__product'))
    
    has_unavailable_items = False
    modified_items = False
    
    for item in items:
        variant = item.variant
        product = variant.product
        category = getattr(product, 'category', None)
        
        item.is_available = True
        
        if (variant.is_deleted or not variant.is_listed or 
            product.is_deleted or not product.is_listed or
            (category and getattr(category, 'is_blocked', False))):
            item.is_available = False
            has_unavailable_items = True
        else:
            site_max = _max_qty_limit()
            allowed_max = min(site_max, variant.stock or 0)
            item.allowed_max = allowed_max
            if item.quantity > allowed_max:
                item.quantity = allowed_max
                item.save()
                modified_items = True
            

    if modified_items:
        messages.info(request, "Quantities for some items were updated due to limited stock.")

    subtotal = Decimal('0')

    for item in items:
        if item.is_available:
            discounted_price = item.variant.product.get_discounted_price()
            item.item_total = discounted_price * item.quantity
            subtotal += item.item_total

    coupon_id = request.session.get('coupon_id')
    coupon = None
    discount = Decimal('0')

    if coupon_id and Coupon:
        coupon = Coupon.objects.filter(id=coupon_id, is_active=True).first()
        if coupon and coupon.is_valid():
            discount = (coupon.discount_percentage / Decimal('100')) * subtotal
            request.session['discount_amount'] = float(discount)
        else:
            request.session.pop('coupon_id', None)
            request.session.pop('discount_amount', None)
            coupon = None

    tax_amount = Decimal('0')
    shipping_amount = Decimal('0')

    total = subtotal + tax_amount + shipping_amount - discount

    if total < 1:
        total = Decimal('1')

    context = {
        'cart': cart,
        'items': items,
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'shipping_amount': shipping_amount,
        'discount': discount,
        'total_price': total,
        'coupon': coupon,
        'has_unavailable_items': has_unavailable_items,
        "cod_limit": settings.COD_LIMIT,
    }

    return render(request, 'cart/cart_page.html', context)


@login_required
def remove_cart_item(request, item_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method.")

    cart = _get_user_cart(request.user)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item.delete()
    messages.success(request, "Removed item from cart.")

    return redirect(reverse('cart:cart_page'))


@login_required
def update_quantity(request, item_id):
    if request.method != 'POST' or request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return HttpResponseBadRequest("Invalid request.")

    cart = _get_user_cart(request.user)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    variant = item.variant

    action = request.POST.get('action')
    qty_val = request.POST.get('qty')

    site_max = _max_qty_limit()
    allowed_max = min(site_max, variant.stock or 0)

    if action == 'increment':
        new_qty = item.quantity + 1
    elif action == 'decrement':
        new_qty = item.quantity - 1
    elif qty_val is not None:
        try:
            new_qty = int(qty_val)
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Invalid quantity'}, status=400)
    else:
        return JsonResponse({'error': 'No action provided'}, status=400)

    new_qty = max(1, min(new_qty, allowed_max))
    message = None
    if action == 'increment' and new_qty >= allowed_max:
        message = f"You can only order maximum {allowed_max}."
    elif action == 'decrement' and new_qty <= 1:
        message = "Minimum one item is required."

    item.quantity = new_qty
    item.save()

    items = cart.items.select_related('variant__product')
    subtotal = sum(
        i.variant.product.get_discounted_price() * i.quantity
        for i in items
    )

    discount = Decimal('0')
    coupon_id = request.session.get('coupon_id')

    if coupon_id and Coupon:
        coupon = Coupon.objects.filter(id=coupon_id, is_active=True).first()
        if coupon and coupon.is_valid():
            if subtotal >= coupon.min_order_amount:
                discount = (coupon.discount_percentage / Decimal('100')) * subtotal
                request.session['discount_amount'] = float(discount)
            else:
                # Remove coupon — minimum amount no longer met
                request.session.pop('coupon_id', None)
                request.session.pop('discount_amount', None)
                return JsonResponse({
                    'error': f'Coupon removed! Minimum order amount should be ₹{coupon.min_order_amount}',
                    'coupon_removed': True,
                    'quantity': item.quantity,
                    'allowed_max': allowed_max,
                    'item_total': float(item.variant.product.get_discounted_price() * item.quantity),
                    'cart_subtotal': float(subtotal),
                    'discount': 0,
                    'cart_total': float(max(subtotal, Decimal('1'))),
                    'cart_items': cart.total_items(),
                }, status=200)

    total = max(subtotal - discount, Decimal('1'))

    return JsonResponse({
        'item_id': item.id,
        'quantity': item.quantity,
        'allowed_max': allowed_max,
        'message': message,
        'item_total': float(item.variant.product.get_discounted_price() * item.quantity),
        'cart_subtotal': float(subtotal),
        'discount': float(discount),
        'cart_total': float(total),
        'cart_items': cart.total_items(),
    })
