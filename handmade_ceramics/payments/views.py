from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

from orders.models import Order, OrderItem
from cart.models import CartItem
from .models import Payment
from .services import get_razorpay_client


@login_required
def start_payment(request, order_id):
    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user,
        is_paid=False,
        status="PENDING"
    )

    amount_in_paise = int(order.total_amount * 100)
    razorpay_client = get_razorpay_client()

    try:
        razorpay_order = razorpay_client.order.create({
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": order.order_id,
            "payment_capture": 1,
        })
    except Exception:
        return redirect('some_order_detail_or_cart_page', order_id=order.order_id)

    payment = Payment.objects.create(
        order=order,
        gateway="RAZORPAY",
        amount=order.total_amount,
        currency="INR",
        status="PENDING",
        razorpay_order_id=razorpay_order["id"]
    )

    context = {
        "order": order,
        "payment": payment,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order["id"],
        "amount": amount_in_paise,
        "currency": "INR",
    }

    return render(request, "payments/razorpay_checkout.html", context)


@csrf_exempt
def verify_payment(request):

    if request.method != "POST":
        return render(request, "payments/payment_failed.html")

    razorpay_payment_id = request.POST.get("razorpay_payment_id")
    razorpay_order_id = request.POST.get("razorpay_order_id")
    razorpay_signature = request.POST.get("razorpay_signature")

    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
        return render(request, "payments/payment_failed.html")

    client = get_razorpay_client()

    try:
        client.utility.verify_payment_signature({
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_order_id": razorpay_order_id,
            "razorpay_signature": razorpay_signature,
        })

        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(
                razorpay_order_id=razorpay_order_id
            )

            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = "SUCCESS"
            payment.save()

            order = payment.order
            order.is_paid = True
            order.status = "CONFIRMED"
            order.payment_method = "RAZORPAY"
            order.save()

            order_items = OrderItem.objects.select_related("variant").filter(order=order)
            for item in order_items:
                item.variant.stock -= item.quantity
                item.variant.save()

            CartItem.objects.filter(cart__user=order.user).delete()

        return render(request, "payments/payment_success.html", {"order": order})

    except Exception:
        Payment.objects.filter(
            razorpay_order_id=razorpay_order_id
        ).update(status="FAILED")

        payment = Payment.objects.filter(
            razorpay_order_id=razorpay_order_id
        ).first()

        if payment and payment.order and not payment.order.is_paid:
            payment.order.delete()

        return render(request, "payments/payment_failed.html")


def payment_success(request):
    return render(request, "payments/payment_success.html")


def payment_failed(request):
    return render(request, "payments/payment_failed.html")


@csrf_exempt
def razorpay_callback(request):

    if request.method != "POST":
        return redirect("payments:failed")

    razorpay_payment_id = request.POST.get("razorpay_payment_id")
    razorpay_order_id = request.POST.get("razorpay_order_id")
    razorpay_signature = request.POST.get("razorpay_signature")

    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
        return redirect("payments:failed")

    razorpay_client = get_razorpay_client()

    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        })

        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(
                razorpay_order_id=razorpay_order_id
            )

            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = "SUCCESS"
            payment.save()

            order = payment.order
            order.is_paid = True
            order.status = "CONFIRMED"
            order.payment_method = "RAZORPAY"
            order.save()

            order_items = OrderItem.objects.select_related("variant").filter(order=order)
            for item in order_items:
                item.variant.stock -= item.quantity
                item.variant.save()

            CartItem.objects.filter(cart__user=order.user).delete()

        return redirect("payments:success")

    except Exception:
        Payment.objects.filter(
            razorpay_order_id=razorpay_order_id
        ).update(status="FAILED")

        return redirect("payments:failed")