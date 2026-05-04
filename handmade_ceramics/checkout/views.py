# checkout/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages

from cart.models import CartItem
from profiles.models import Address
from orders.models import Order, OrderItem
from coupons.models import Coupon, CouponUsage
from decimal import Decimal
from coupons.models import Coupon, CouponUsage
from django.db import transaction

from wallet.services import debit_wallet
from wallet.models import Wallet
from django.conf import settings

@login_required
def checkout_page(request):
    user = request.user

    cart_items = CartItem.objects.filter(
        cart__user=user,
        variant__isnull=False,
        variant__product__isnull=False
    ).select_related("variant", "variant__product")

    has_unavailable_items = False
    for item in cart_items:
        variant = item.variant
        product = variant.product
        category = getattr(product, 'category', None)
        
        if (variant.is_deleted or not variant.is_listed or 
            product.is_deleted or not product.is_listed or
            (category and getattr(category, 'is_blocked', False))):
            has_unavailable_items = True
            break

    if has_unavailable_items:
        messages.warning(request, "Please remove unavailable items from your cart before proceeding to checkout.")
        return redirect("cart:cart_page")

    if not cart_items.exists():
        return redirect("cart:cart_page")

    subtotal = sum(
        item.variant.product.get_discounted_price() * item.quantity
        for item in cart_items
    )

    tax_amount = 0
    shipping_amount = Decimal('0') if subtotal >= Decimal('1000') else Decimal('50')

    discount = Decimal(str(request.session.get("discount_amount", 0)))
    coupon_id = request.session.get("coupon_id")

    coupon = None
    if coupon_id:
        coupon = Coupon.objects.filter(id=coupon_id).first()

    total = subtotal + tax_amount + shipping_amount - discount

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
        "cod_limit": settings.COD_LIMIT,
    }

    return render(request, "checkout/checkout.html", context)


@login_required
@transaction.atomic
def place_order(request):
    if request.method != "POST":
        return redirect("checkout:checkout")

    user = request.user
    address_id = request.POST.get("address_id")
    payment_method = request.POST.get("payment_method", "COD")

    if not address_id:
        return redirect("checkout:checkout")

    address = get_object_or_404(Address, id=address_id, user=user)

    cart_items = (
        CartItem.objects
        .filter(cart__user=user, variant__isnull=False, variant__is_deleted=False,
                variant__product__isnull=False, variant__product__is_deleted=False)
        .select_related("variant__product")
        .select_for_update()
    )

    if not cart_items.exists():
        return redirect("checkout:checkout")

    for item in cart_items:
        variant = item.variant
        product = variant.product
        category = getattr(product, "category", None)

        if variant.is_deleted or not variant.is_listed:
            messages.error(request, f"{product.name} is no longer available.")
            return redirect("cart:cart_page")

        if product.is_deleted or not product.is_listed:
            messages.error(request, f"{product.name} is currently unavailable.")
            return redirect("cart:cart_page")

        if category and getattr(category, "is_blocked", False):
            messages.error(request, f"{product.name} cannot be ordered right now.")
            return redirect("cart:cart_page")

        if item.quantity > variant.stock:
            messages.error(request, f"Only {variant.stock} items available for {product.name}.")
            return redirect("checkout:checkout")

    subtotal = sum(
        item.variant.product.get_discounted_price() * item.quantity
        for item in cart_items
    )
    tax_amount = 0
    shipping_amount = Decimal('0') if subtotal >= Decimal('1000') else Decimal('50')

    discount = Decimal(str(request.session.get("discount_amount", 0)))
    coupon_id = request.session.get("coupon_id")
    coupon = None
    if coupon_id:
        coupon = Coupon.objects.filter(id=coupon_id, is_active=True).first()
    total = subtotal + tax_amount + shipping_amount - discount

    if payment_method == "COD" and total > settings.COD_LIMIT:
        messages.error(
            request,
            f"Cash on Delivery is not available for orders above ₹{settings.COD_LIMIT}."
        )
        return redirect("checkout:checkout")

    if payment_method == "COD":
        order_status = "PENDING"   
        is_paid = False            
    else:
        order_status = "PENDING"
        is_paid = False

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
        payment_method=payment_method,
        status=order_status,
        is_paid=is_paid,
        coupon=coupon if coupon else None,
    )

    if coupon:
        request.session.pop('coupon_id', None)
        request.session.pop('discount_amount', None)

    for item in cart_items:
        item_unit_price = item.variant.product.get_discounted_price()
        item_subtotal = item_unit_price * item.quantity
        
        item_discount = Decimal("0.00")
        if coupon and subtotal > 0:
            item_discount = (item_subtotal * Decimal(coupon.discount_percentage)) / Decimal("100")
            item_discount = item_discount.quantize(Decimal("0.01"))

        OrderItem.objects.create(
            order=order,
            product=item.variant.product,
            variant=item.variant,
            product_name=item.variant.product.name,
            variant_color=item.variant.color or "",
            unit_price=item_unit_price,
            quantity=item.quantity,
            coupon_discount_amount=item_discount
        )

    if payment_method == "COD":
        if coupon:
            CouponUsage.objects.create(user=user, coupon=coupon, order=order)

        for item in cart_items:
            item.variant.stock -= item.quantity
            item.variant.save()

        CartItem.objects.filter(cart__user=user).delete()
        return redirect("checkout:success", order_id=order.order_id)

    elif payment_method == "WALLET":
        wallet = Wallet.objects.select_for_update().get(user=request.user)
        
        if wallet.balance < order.total_amount:
            messages.error(request, "Insufficient wallet balance")
            return redirect("checkout:checkout")
        
        debit_wallet(wallet, order.total_amount, f"Payment for order {order.order_id}", order=order)

        order.is_paid = True
        order.payment_method = "WALLET"
        order.status = "CONFIRMED"
        order.save()

        if coupon:
            CouponUsage.objects.create(user=user, coupon=coupon, order=order)

        for item in cart_items:
            item.variant.stock -= item.quantity
            item.variant.save()

        CartItem.objects.filter(cart__user=request.user).delete()

        messages.success(request, "Order paid using wallet.")
        return redirect("checkout:success", order_id=order.order_id)


    else:
        return redirect("payments:start", order_id=order.order_id)




@login_required
def checkout_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)

    return render(request, 'checkout/success.html', {
        'order': order,
        'order_id': order.order_id
    })
