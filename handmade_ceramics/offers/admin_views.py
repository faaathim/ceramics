from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import ProductOffer, CategoryOffer
from .forms import ProductOfferForm, CategoryOfferForm

def superuser_check(user):
    return user.is_active and user.is_superuser


# product offer list
@login_required
@user_passes_test(superuser_check)
def product_offer_list(request):
    offers = ProductOffer.objects.select_related('product').order_by('-created_at')

    return render(request, 'offers/product_offer_list.html', {'offers': offers})


# create product offer
@login_required
@user_passes_test(superuser_check)
def product_offer_create(request):
    if request.method == 'POST':
        form = ProductOfferForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Product offer created successfully.")
            return redirect('custom_admin:offers:product_offer_list')
    else:
        form = ProductOfferForm()

    return render(request, 'offers/product_offer_form.html', {'form': form})


# toggle product offer 
@login_required
@user_passes_test(superuser_check)
def product_offer_toggle(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)
    offer.is_active = not offer.is_active
    offer.save()

    messages.success(request, "Offer status updated.")
    return redirect('custom_admin:offers:product_offer_list')


# edit product offer
@login_required
@user_passes_test(superuser_check)
def product_offer_edit(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)

    if request.method == 'POST':
        form = ProductOfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, "Product offer updated successfully.")
            return redirect('custom_admin:offers:product_offer_list')
    else:
        form = ProductOfferForm(instance=offer)

    return render(request, 'offers/product_offer_form.html', {'form': form})


# delete product offer 
@login_required 
@user_passes_test(superuser_check)
def product_offer_delete(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)

    if request.method == 'POST':
        offer.delete()
        messages.success(request, "Product offer deleted.")
        return redirect('custom_admin:offers:product_offer_list')
    
    return render(request, 'offers/offer_confirm_delete.html', {'offer': offer})


# category offer list
@login_required
@user_passes_test(superuser_check)
def category_offer_list(request):
    offers = CategoryOffer.objects.select_related('category').order_by('-created_at')

    return render(request, 'offers/category_offer_list.html', {'offers': offers})


# create category offer 
@login_required
@user_passes_test(superuser_check)
def category_offer_create(request):
    if request.method == 'POST':
        form = CategoryOfferForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category offer created successfully.")
            return redirect('custom_admin:offers:category_offer_list')
        
    else:
        form = CategoryOfferForm()

    return render(request, 'offers/category_offer_form.html', {'form': form})


# edit category offer
@login_required
@user_passes_test(superuser_check)
def category_offer_edit(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)

    if request.method == 'POST':
        form = CategoryOfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, "Category offer updated successfully.")
            return redirect('custom_admin:offers:category_offer_list')
        
    else:
        form = CategoryOfferForm(instance=offer)
    
    return render(request, 'offers/category_offer_form.html', {'form': form})


# delete category offer
@login_required
@user_passes_test(superuser_check)
def category_offer_delete(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)

    if request.method == 'POST':
        offer.delete()
        messages.success(request, "Category offer deleted.")
        return redirect('custom_admin:offers:category_offer_list')

    # For GET request
    return render(request, 'offers/offer_confirm_delete.html', {'offer': offer})

    

# toggle category offer
@login_required
@user_passes_test(superuser_check)
def category_offer_toggle(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)

    offer.is_active = not offer.is_active
    offer.save()

    messages.success(request, "Category offer status updated.")
    return redirect('custom_admin:offers:category_offer_list')

