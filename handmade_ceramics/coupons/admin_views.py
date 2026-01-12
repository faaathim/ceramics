from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import Coupon
from .forms import CouponForm

def superuser_check(user):
    return user.is_active and user.is_superuser

@login_required
@user_passes_test(superuser_check)
def coupon_list(request):
    coupons = Coupon.objects.all().order_by('-created_at')

    return render(request, 'coupons/coupon_list.html', {
        'coupons': coupons
    })

@login_required
@user_passes_test(superuser_check)
def coupon_create(request):
    if request.method == 'POST':
        form = CouponForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Coupon created successfully.")
            return redirect('custom_admin:coupons:coupon_list')
        else:
            messages.error(request, "Please fix the errors below.")

    else:
        form = CouponForm()

    return render(request, 'coupons/coupon_create.html', {
        'form': form
    })

@login_required
@user_passes_test(superuser_check)
def coupon_toggle(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.is_active = not coupon.is_active
    coupon.save()

    status = "activated" if coupon.is_active else "deactivated"
    messages.success(request, f"Coupon {status} successfully.")

    return redirect('custom_admin:coupons:coupon_list')

@login_required
@user_passes_test(superuser_check)
def coupon_edit(request, coupon_id):
    """
    Edit an existing coupon
    """
    coupon = get_object_or_404(Coupon, id=coupon_id)

    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)

        if form.is_valid():
            form.save()
            messages.success(request, "Coupon updated successfully.")
            return redirect('custom_admin:coupons:coupon_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = CouponForm(instance=coupon)

    return render(request, 'coupons/coupon_edit.html', {
        'form': form,
        'coupon': coupon
    })


@login_required
@user_passes_test(superuser_check)
def coupon_delete(request, coupon_id):
    """
    Delete a coupon (with confirmation)
    """
    coupon = get_object_or_404(Coupon, id=coupon_id)

    if request.method == 'POST':
        coupon.delete()
        messages.success(request, "Coupon deleted successfully.")
        return redirect('custom_admin:coupons:coupon_list')

    return render(request, 'coupons/coupon_confirm_delete.html', {
        'coupon': coupon
    })


