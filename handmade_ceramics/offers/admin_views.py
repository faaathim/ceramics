from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError

from .models import ProductOffer, CategoryOffer
from .forms import ProductOfferForm, CategoryOfferForm


def superuser_check(user):
    return user.is_active and user.is_superuser


# =========================
# PRODUCT OFFERS
# =========================

@login_required
@user_passes_test(superuser_check)
def product_offer_list(request):
    offers = ProductOffer.objects.select_related('product').order_by('-created_at')
    return render(request, 'offers/product_offer_list.html', {'offers': offers})


@login_required
@user_passes_test(superuser_check)
def product_offer_create(request):
    form = ProductOfferForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Product offer created successfully.")
                return redirect('custom_admin:offers:product_offer_list')

            except ValidationError as e:
                form.add_error(None, e.message)

        else:
            messages.error(request, "Please correct the highlighted errors.")

    return render(request, 'offers/product_offer_form.html', {'form': form})


@login_required
@user_passes_test(superuser_check)
def product_offer_edit(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)
    form = ProductOfferForm(request.POST or None, instance=offer)

    if request.method == "POST":
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Product offer updated successfully.")
                return redirect('custom_admin:offers:product_offer_list')

            except ValidationError as e:
                form.add_error(None, e.message)

        else:
            messages.error(request, "Please correct the highlighted errors.")

    return render(request, 'offers/product_offer_form.html', {'form': form})


@login_required
@user_passes_test(superuser_check)
def product_offer_toggle(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)

    offer.is_active = not offer.is_active

    try:
        offer.save()
        messages.success(
            request,
            f"Offer {'activated' if offer.is_active else 'deactivated'} successfully."
        )

    except ValidationError as e:
        if hasattr(e, "message_dict"):
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, f"{error}")
        else:
            for error in e.messages:
                messages.error(request, error)

    return redirect('custom_admin:offers:product_offer_list')


@login_required
@user_passes_test(superuser_check)
def product_offer_delete(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)

    if request.method == "POST":
        offer.delete()
        messages.success(request, "Product offer deleted successfully.")
        return redirect('custom_admin:offers:product_offer_list')

    return render(request, 'offers/offer_confirm_delete.html', {'offer': offer})


# =========================
# CATEGORY OFFERS
# =========================

@login_required
@user_passes_test(superuser_check)
def category_offer_list(request):
    offers = CategoryOffer.objects.select_related('category').order_by('-created_at')
    return render(request, 'offers/category_offer_list.html', {'offers': offers})


@login_required
@user_passes_test(superuser_check)
def category_offer_create(request):
    form = CategoryOfferForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Category offer created successfully.")
                return redirect('custom_admin:offers:category_offer_list')

            except ValidationError as e:
                form.add_error(None, e.message)

        else:
            messages.error(request, "Please correct the highlighted errors.")

    return render(request, 'offers/category_offer_form.html', {'form': form})


@login_required
@user_passes_test(superuser_check)
def category_offer_edit(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)
    form = CategoryOfferForm(request.POST or None, instance=offer)

    if request.method == "POST":
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Category offer updated successfully.")
                return redirect('custom_admin:offers:category_offer_list')

            except ValidationError as e:
                form.add_error(None, e.message)

        else:
            messages.error(request, "Please correct the highlighted errors.")

    return render(request, 'offers/category_offer_form.html', {'form': form})


@login_required
@user_passes_test(superuser_check)
def category_offer_toggle(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)

    offer.is_active = not offer.is_active

    try:
        offer.save()
        messages.success(
            request,
            f"Category offer {'activated' if offer.is_active else 'deactivated'} successfully."
        )

    except ValidationError as e:
        if hasattr(e, "message_dict"):
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, f"{error}")
        else:
            for error in e.messages:
                messages.error(request, error)

    return redirect('custom_admin:offers:category_offer_list')


@login_required
@user_passes_test(superuser_check)
def category_offer_delete(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)

    if request.method == "POST":
        offer.delete()
        messages.success(request, "Category offer deleted successfully.")
        return redirect('custom_admin:offers:category_offer_list')

    return render(request, 'offers/offer_confirm_delete.html', {'offer': offer})