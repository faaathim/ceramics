from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from cart.models import CartItem
from user_addresses.models import Address
from orders.models import Order, OrderItem


@login_required
def checkout_page(request):
    user = request.user

    # Only get cart items with valid variant and product
    cart_items = CartItem.objects.filter(
        cart__user=user,
        variant__isnull=False,
        variant__product__isnull=False
    ).select_related("variant", "variant__product")

    if not cart_items.exists():
        return redirect("cart_app:cart")  # redirect if cart is empty

    subtotal = sum(item.variant.product.price * item.quantity for item in cart_items)
    tax_amount = 0
    shipping_amount = 0
    discount = 0
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
        "selected_address_id": request.GET.get("address_id"),
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

    # Get the address safely
    try:
        address = Address.objects.get(id=address_id, user=user)
    except Address.DoesNotExist:
        return redirect("checkout:checkout")

    # Get valid cart items (only saved, not-deleted variants/products)
    cart_items = CartItem.objects.filter(
        cart__user=user,
        variant__isnull=False,
        variant__is_deleted=False,
        variant__product__isnull=False,
        variant__product__is_deleted=False,
    ).select_related("variant__product")

    if not cart_items.exists():
        return redirect("checkout:checkout")

    subtotal = sum(item.variant.product.price * item.quantity for item in cart_items)
    tax_amount = 0
    shipping_amount = 0
    discount = 0
    total = subtotal + tax_amount + shipping_amount - discount

    # Create the order with correct address mapping
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
    )

    # Create order items safely
    for item in cart_items:
        variant = item.variant
        product = variant.product

        # Skip if variant or product has no ID (unsaved)
        if not variant.id or not product.id:
            continue

        OrderItem.objects.create(
            order=order,
            product=product,
            variant=variant,
            product_name=product.name,
            variant_color=variant.color,
            unit_price=product.price,
            quantity=item.quantity,
        )

        # Reduce stock safely
        variant.stock = max(variant.stock - item.quantity, 0)
        variant.save()

    # Clear user's cart
    CartItem.objects.filter(cart__user=user).delete()

    return redirect("checkout:success", order_id=order.order_id)


@login_required
def checkout_success(request, order_id):
    # Correct: lookup by order_id (string)
    order = get_object_or_404(Order, order_id=order_id)

    return render(request, 'checkout/success.html', {
        'order': order,
        'order_id': order.order_id  # pass the string to template
    })


