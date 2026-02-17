# coupons/views.py

from decimal import Decimal

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Coupon, CouponUsage
from cart.models import CartItem


# ---------------------------------------------------
# Apply Coupon
# ---------------------------------------------------

@login_required
def apply_coupon(request):
    """
    Apply a coupon code to the user's cart.

    - Validates coupon
    - Checks minimum order amount
    - Prevents reuse
    - Stores coupon data in session
    """
    if request.method != 'POST':
        return redirect('cart:cart_page')

    # Read and normalize coupon code
    coupon_code = request.POST.get('coupon_code', '').strip().upper()

    if not coupon_code:
        messages.error(request, 'Please enter a coupon code.')
        return redirect('cart:cart_page')

    # Check if coupon exists and is active
    try:
        coupon = Coupon.objects.get(code=coupon_code, is_active=True)
    except Coupon.DoesNotExist:
        messages.error(request, 'Invalid coupon code.')
        return redirect('cart:cart_page')

    # Check expiry / validity
    if not coupon.is_valid():
        messages.error(request, 'This coupon has expired.')
        return redirect('cart:cart_page')

    # Prevent coupon reuse by same user
    if CouponUsage.objects.filter(user=request.user, coupon=coupon).exists():
        messages.error(request, 'You have already used this coupon.')
        return redirect('cart:cart_page')

    # Fetch cart items
    cart_items = CartItem.objects.filter(
        cart__user=request.user
    ).select_related('variant__product')

    if not cart_items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('cart:cart_page')

    # Calculate subtotal (price × quantity)
    subtotal = sum(
        Decimal(item.variant.product.get_discounted_price()) * item.quantity
        for item in cart_items
    )

    # Minimum order amount check
    if subtotal < coupon.min_order_amount:
        messages.error(
            request,
            f'Minimum order amount of ₹{coupon.min_order_amount} is required.'
        )
        return redirect('cart:cart_page')

    # Calculate discount
    discount = (Decimal(coupon.discount_percentage) / Decimal('100')) * subtotal

    # Ensure minimum payable amount of ₹1
    if subtotal - discount < 1:
        discount = subtotal - 1

    # Store coupon info in session
    request.session['coupon_id'] = coupon.id
    request.session['discount_amount'] = float(discount)

    messages.success(
        request,
        f'Coupon "{coupon.code}" applied! You saved ₹{int(discount)}.'
    )

    return redirect('cart:cart_page')


# ---------------------------------------------------
# Remove Coupon
# ---------------------------------------------------

@login_required
def remove_coupon(request):
    """
    Remove the applied coupon from the cart.
    """
    request.session.pop('coupon_id', None)
    request.session.pop('discount_amount', None)

    messages.info(request, 'Coupon removed from cart.')
    return redirect('cart:cart_page')
