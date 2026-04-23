# coupons/views.py 

from decimal import Decimal

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from coupons.models import Coupon, CouponUsage
from cart.models import CartItem

@login_required
def apply_coupon(request):

    if request.method != 'POST':
        return redirect('cart:cart_page')

    coupon_code = request.POST.get('coupon_code', '').strip().upper()

    if not coupon_code:
        messages.error(request, 'Please enter a coupon code.')
        return redirect('cart:cart_page')

    try:
        coupon = Coupon.objects.get(code=coupon_code, is_active=True)
    except Coupon.DoesNotExist:
        messages.error(request, 'Invalid coupon code.')
        return redirect('cart:cart_page')

    if not coupon.is_valid():
        messages.error(request, 'This coupon has expired.')
        return redirect('cart:cart_page')

    # ── Already applied to the current session ────────────────────────────────
    if request.session.get('coupon_id') == coupon.id:
        messages.warning(request, f'Coupon "{coupon.code}" is already applied to your cart.')
        return redirect('cart:cart_page')

    # ── Already used in a completed order ─────────────────────────────────────
    if CouponUsage.objects.filter(user=request.user, coupon=coupon).exists():
        messages.error(request, 'You have already used this coupon.')
        return redirect('cart:cart_page')

    cart_items = CartItem.objects.filter(
        cart__user=request.user
    ).select_related('variant__product')

    if not cart_items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('cart:cart_page')

    subtotal = sum(
        Decimal(item.variant.product.get_discounted_price()) * item.quantity
        for item in cart_items
    )

    if subtotal < coupon.min_order_amount:
        messages.error(
            request,
            f'Minimum order amount of ₹{coupon.min_order_amount} is required.'
        )
        return redirect('cart:cart_page')

    discount = (Decimal(coupon.discount_percentage) / Decimal('100')) * subtotal

    if subtotal - discount < 1:
        discount = subtotal - 1

    request.session['coupon_id'] = coupon.id
    request.session['discount_amount'] = float(discount)

    messages.success(
        request,
        f'Coupon "{coupon.code}" applied! You saved ₹{int(discount)}.'
    )

    return redirect('cart:cart_page')


@login_required
def remove_coupon(request):

    request.session.pop('coupon_id', None)
    request.session.pop('discount_amount', None)

    messages.info(request, 'Coupon removed from cart.')
    return redirect('cart:cart_page')