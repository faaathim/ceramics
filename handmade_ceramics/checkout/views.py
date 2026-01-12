from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages

from cart.models import CartItem
from user_addresses.models import Address
from orders.models import Order, OrderItem
from coupons.models import Coupon, CouponUsage
from decimal import Decimal
from coupons.models import Coupon, CouponUsage
from django.db import transaction



@login_required
def checkout_page(request):
    user = request.user

    cart_items = CartItem.objects.filter(
        cart__user=user,
        variant__isnull=False,
        variant__product__isnull=False
    ).select_related("variant", "variant__product")

    if not cart_items.exists():
        return redirect("cart:cart_page")

    subtotal = sum(
        item.variant.product.price * item.quantity
        for item in cart_items
    )

    tax_amount = 0
    shipping_amount = 0

    # ✅ READ FROM SESSION ONLY
    discount = Decimal(str(request.session.get("discount_amount", 0)))
    coupon_id = request.session.get("coupon_id")

    coupon = None
    if coupon_id:
        coupon = Coupon.objects.filter(id=coupon_id).first()

    total = subtotal + tax_amount + shipping_amount - discount

    # Safety: never allow negative total
    if total < 1:
        total = 1

    addresses = Address.objects.filter(user=user, is_deleted=False)

    context = {
        "cart_items": cart_items,
        "addresses": addresses,
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "shipping_amount": shipping_amount,
        "discount": discount,
        "total": total,
        "coupon": coupon,
    }

    return render(request, "checkout/checkout.html", context)


@login_required
@transaction.atomic
def place_order(request):
    if request.method != "POST":
        return redirect("checkout:checkout")

    user = request.user
    address_id = request.POST.get("address_id")

    if not address_id:
        return redirect("checkout:checkout")

    # ✅ Get user address
    address = get_object_or_404(Address, id=address_id, user=user)

    # ✅ Lock cart items to prevent overselling
    cart_items = (
        CartItem.objects
        .filter(
            cart__user=user,
            variant__isnull=False,
            variant__is_deleted=False,
            variant__product__isnull=False,
            variant__product__is_deleted=False,
        )
        .select_related("variant__product")
        .select_for_update()
    )

    if not cart_items.exists():
        return redirect("checkout:checkout")

    # ✅ Check stock
    for item in cart_items:
        if item.quantity > item.variant.stock:
            messages.error(
                request,
                f"Not enough stock for {item.variant.product.name}"
            )
            return redirect("checkout:checkout")

    # ✅ Calculate subtotal
    subtotal = sum(
        (item.variant.product.price * item.quantity)
        for item in cart_items
    ) or Decimal("0")


    tax_amount = 0
    shipping_amount = 0

    # ✅ Fetch coupon safely from session
    coupon_id = request.session.get('coupon_id')
    coupon = None
    discount = Decimal("0")

    if coupon_id:
        coupon = Coupon.objects.filter(id=coupon_id, is_active=True).first()

    # ✅ Re-validate coupon fully
    if coupon:
        # Expiry check
        if not coupon.is_valid():
            coupon = None
        # Minimum order amount check
        elif subtotal < coupon.min_order_amount:
            coupon = None
        # Check if user already used it
        elif CouponUsage.objects.filter(user=user, coupon=coupon).exists():
            coupon = None

        # Remove invalid coupon from session
        if not coupon:
            request.session.pop('coupon_id', None)
            request.session.pop('discount_amount', None)

    # ✅ Recalculate discount safely
    if coupon:
        discount_percentage = Decimal(str(coupon.discount_percentage))
        discount = (discount_percentage / Decimal("100")) * subtotal

    # Ensure minimum ₹1 payable
    if subtotal - discount < 1:
        discount = subtotal - Decimal("1")


    # ✅ Calculate final total
    total = subtotal + tax_amount + shipping_amount - discount
    if total < 1:
        total = 1

    # ✅ Create order atomically
    order = Order.objects.create(
        user=user,
        shipping_full_name=f"{address.first_name} {address.last_name}".strip(),
        shipping_phone=address.phone,
        shipping_email=user.email,
        shipping_address_line=address.street_address,
        shipping_city=address.city,
        shipping_state=address.state,
        shipping_pincode=address.pin_code,
        subtotal=subtotal,
        tax_amount=tax_amount,
        shipping_charge=shipping_amount,
        discount_amount=discount,
        total_amount=total,
        payment_method="COD",
        coupon=coupon if coupon else None,
    )

    # ✅ Save coupon usage
    if coupon:
        CouponUsage.objects.create(
            user=user,
            coupon=coupon,
            order=order
        )
        # Clear coupon session
        request.session.pop('coupon_id', None)
        request.session.pop('discount_amount', None)

    # ✅ Reduce stock & create order items
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.variant.product,
            variant=item.variant,
            product_name=item.variant.product.name,
            variant_color=item.variant.color or "",
            unit_price=item.variant.product.price,
            quantity=item.quantity
        )
        # Reduce stock safely
        item.variant.stock -= item.quantity
        item.variant.save()

    # ✅ Clear cart
    CartItem.objects.filter(cart__user=user).delete()

    return redirect("checkout:success", order_id=order.order_id)



@login_required
def checkout_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)

    return render(request, 'checkout/success.html', {
        'order': order,
        'order_id': order.order_id
    })
