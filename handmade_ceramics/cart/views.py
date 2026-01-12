from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import HttpResponseBadRequest, JsonResponse
from django.urls import reverse

from .models import Cart, CartItem
from product_management.models import Variant

# Optional models (app may not exist yet)
try:
    from product_management.models import Wishlist
except Exception:
    Wishlist = None

try:
    from coupons.models import Coupon
except Exception:
    Coupon = None


# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------

def _max_qty_limit():
    """
    Maximum quantity allowed per cart item (site-wide).
    Can be configured in settings.py:
        CART_MAX_QTY_PER_ITEM = 10
    """
    return getattr(settings, 'CART_MAX_QTY_PER_ITEM', 10)


def _get_user_cart(user):
    """
    Get or create the cart for the logged-in user.
    Each user always has exactly one cart.
    """
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


# -------------------------------------------------------------------
# Add to cart
# -------------------------------------------------------------------

@login_required
def add_to_cart(request):
    """
    Add a product variant to the user's cart.

    POST data:
      - variant_id (required)
      - qty (optional, defaults to 1)

    Validations:
      - Variant and product must be active
      - Category must not be blocked
      - Quantity must respect stock and site limit
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method.")

    # Read variant id safely
    try:
        variant_id = int(request.POST.get('variant_id'))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("Invalid variant id.")

    # Read quantity (default = 1)
    try:
        qty_requested = int(request.POST.get('qty', 1))
    except (TypeError, ValueError):
        qty_requested = 1

    if qty_requested < 1:
        qty_requested = 1

    # Fetch variant
    variant = get_object_or_404(Variant, pk=variant_id)

    # Validate variant and product
    if variant.is_deleted or not variant.is_listed:
        return HttpResponseBadRequest("This variant is not available.")

    product = variant.product
    if product.is_deleted or not product.is_listed:
        return HttpResponseBadRequest("This product is not available.")

    # Optional category block check
    category = getattr(product, 'category', None)
    if category and getattr(category, 'is_blocked', False):
        return HttpResponseBadRequest("This category is blocked.")

    # Determine max quantity allowed
    site_max = _max_qty_limit()
    allowed_max = min(site_max, variant.stock or 0)

    if allowed_max <= 0:
        return HttpResponseBadRequest("This variant is out of stock.")

    qty_to_add = min(qty_requested, allowed_max)

    # Get user's cart
    cart = _get_user_cart(request.user)

    # Add or update cart item
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant
    )

    if created:
        cart_item.quantity = qty_to_add
    else:
        cart_item.quantity = min(cart_item.quantity + qty_to_add, allowed_max)

    cart_item.save()

    # Remove item from wishlist if it exists
    if Wishlist:
        Wishlist.objects.filter(user=request.user, variant=variant).delete()

    return redirect(reverse('cart:cart_page'))


# -------------------------------------------------------------------
# Cart page
# -------------------------------------------------------------------

@login_required
def cart_page(request):
    """
    Display the cart page with subtotal, coupon discount, and total.
    """
    cart = _get_user_cart(request.user)
    items = cart.items.select_related('variant__product')

    # Calculate subtotal (price × quantity)
    subtotal = sum(
        Decimal(item.variant.product.price) * item.quantity
        for item in items
    )

    # Coupon handling
    coupon_id = request.session.get('coupon_id')
    coupon = None
    discount = Decimal('0')

    if coupon_id and Coupon:
        coupon = Coupon.objects.filter(id=coupon_id, is_active=True).first()
        if coupon and coupon.is_valid():
            discount = (coupon.discount_percentage / Decimal('100')) * subtotal
            request.session['discount_amount'] = float(discount)
        else:
            # Remove invalid coupon
            request.session.pop('coupon_id', None)
            request.session.pop('discount_amount', None)
            coupon = None

    # Extra charges (kept simple for beginners)
    tax_amount = Decimal('0')
    shipping_amount = Decimal('0')

    total = subtotal + tax_amount + shipping_amount - discount

    # Ensure minimum payable amount
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
    }

    return render(request, 'cart/cart_page.html', context)


# -------------------------------------------------------------------
# Remove item from cart
# -------------------------------------------------------------------

@login_required
def remove_cart_item(request, item_id):
    """
    Remove a single item from the cart.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method.")

    cart = _get_user_cart(request.user)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item.delete()

    return redirect(reverse('cart:cart_page'))


# -------------------------------------------------------------------
# Update quantity (AJAX)
# -------------------------------------------------------------------

@login_required
def update_quantity(request, item_id):
    """
    Update quantity for a cart item using AJAX.

    POST data:
      - action = increment | decrement
      - OR qty = <number>

    Returns updated totals as JSON.
    """
    if request.method != 'POST' or request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return HttpResponseBadRequest("Invalid request.")

    cart = _get_user_cart(request.user)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    variant = item.variant

    action = request.POST.get('action')
    qty_val = request.POST.get('qty')

    site_max = _max_qty_limit()
    allowed_max = min(site_max, variant.stock or 0)

    # Determine new quantity
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

    # Enforce limits
    new_qty = max(1, min(new_qty, allowed_max))

    item.quantity = new_qty
    item.save()

    # Recalculate totals
    items = cart.items.select_related('variant__product')
    subtotal = sum(
        Decimal(i.variant.product.price) * i.quantity
        for i in items
    )

    discount = Decimal('0')
    coupon_id = request.session.get('coupon_id')

    if coupon_id and Coupon:
        coupon = Coupon.objects.filter(id=coupon_id, is_active=True).first()
        if coupon and coupon.is_valid():
            discount = (coupon.discount_percentage / Decimal('100')) * subtotal

    total = subtotal - discount
    if total < 1:
        total = Decimal('1')

    return JsonResponse({
        'item_id': item.id,
        'quantity': item.quantity,
        'item_total': float(Decimal(item.variant.product.price) * item.quantity),
        'cart_subtotal': float(subtotal),
        'discount': float(discount),
        'cart_total': float(total),
        'cart_items': cart.total_items(),
    })
