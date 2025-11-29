from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import HttpResponseBadRequest
from django.urls import reverse

from .models import Cart, CartItem
from product_management.models import Variant, Product

# Optional: if you implement Wishlist model later, import here. For now we guard its use.
try:
    from product_management.models import Wishlist
except Exception:
    Wishlist = None


def _max_qty_limit():
    """
    Return site-wide max per-item limit from settings, default to 10.
    """
    return getattr(settings, 'CART_MAX_QTY_PER_ITEM', 10)


def _get_user_cart(user):
    """
    Return (or create) the Cart for a user.
    Using OneToOne on Cart makes it easy: each user has one cart row.
    """
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def add_to_cart(request):
    """
    Add a variant to user's cart. POST only.
    Expects POST fields: variant_id, qty (optional).
    Validates: variant listed, product listed, category not blocked (if attribute exists),
               quantity <= stock and <= site max.
    If item already exists => increase quantity (respecting limits).
    If Wishlist exists => remove the variant from wishlist.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method. Use POST to add to cart.")

    # read and validate variant_id
    try:
        variant_id = int(request.POST.get('variant_id', 0))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("Invalid variant id.")

    # read qty or default to 1
    try:
        qty_requested = int(request.POST.get('qty', 1))
    except (TypeError, ValueError):
        qty_requested = 1
    if qty_requested < 1:
        qty_requested = 1

    # fetch variant
    variant = get_object_or_404(Variant, pk=variant_id)

    # Validation 1: variant must be listed and not deleted
    if variant.is_deleted or not variant.is_listed:
        return HttpResponseBadRequest("This variant is not available.")

    # Validation 2: product must be listed and not deleted
    product = variant.product
    if product.is_deleted or not product.is_listed:
        return HttpResponseBadRequest("This product is not available.")

    # Validation 3: category-level block (if your Category has is_blocked attribute)
    category = getattr(product, 'category', None)
    if category and getattr(category, 'is_blocked', False):
        return HttpResponseBadRequest("Product category is blocked.")

    # Determine maximum allowed quantity for this variant
    site_max = _max_qty_limit()
    allowed_max = min(site_max, variant.stock or 0)
    if allowed_max <= 0:
        return HttpResponseBadRequest("This variant is out of stock.")

    # final qty to add (cap by allowed_max)
    qty_to_add = min(qty_requested, allowed_max)

    # get/create user's cart
    cart = _get_user_cart(request.user)

    # get or create cart item
    cart_item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)

    if created:
        cart_item.quantity = qty_to_add
    else:
        # increase but don't exceed allowed_max
        new_qty = cart_item.quantity + qty_to_add
        cart_item.quantity = min(new_qty, allowed_max)

    cart_item.save()

    # If a wishlist model exists, remove this variant from it for this user
    if Wishlist:
        try:
            Wishlist.objects.filter(user=request.user, variant=variant).delete()
        except Exception:
            pass  # ignore wishlist errors for now

    # Redirect to cart page (could return JSON for AJAX later)
    return redirect(reverse('cart:cart_page'))


@login_required
def cart_page(request):
    """
    Show the user's cart page.
    """
    cart = _get_user_cart(request.user)
    items = cart.items.select_related('variant__product').all()
    context = {
        'cart': cart,
        'items': items,
        'total_price': cart.total_price(),
    }
    return render(request, 'cart/cart_page.html', context)


@login_required
def remove_cart_item(request, item_id):
    """
    Remove a CartItem from the cart. Accepts POST.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method.")

    cart = _get_user_cart(request.user)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item.delete()
    return redirect(reverse('cart:cart_page'))


@login_required
def update_quantity(request, item_id):
    """
    Update quantity for a cart item.
    Accepts POST with either:
      - action = 'increment' or 'decrement'
      - or qty = <int> to set absolute value

    Ensures 1 <= quantity <= min(variant.stock, site_max).
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method.")

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
        except (ValueError, TypeError):
            return HttpResponseBadRequest("Invalid quantity.")
    else:
        return HttpResponseBadRequest("No action provided.")

    if new_qty < 1:
        new_qty = 1
    if new_qty > allowed_max:
        new_qty = allowed_max

    item.quantity = new_qty
    item.save()
    return redirect(reverse('cart:cart_page'))
