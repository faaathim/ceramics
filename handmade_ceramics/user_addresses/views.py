# user_addresses/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Address
from .forms import AddressForm
from user_profile.models import Profile  # Import Profile model


@login_required
def address_list(request):
    # Get user's profile to show in sidebar
    profile = Profile.objects.get(user=request.user)
    addresses = Address.objects.filter(user=request.user, is_deleted=False)
    return render(request, 'user_addresses/address_list.html', {
        'addresses': addresses,
        'profile': profile  # Send profile to template
    })


@login_required
def address_add(request):
    next_page = request.GET.get("next", "address_list")  # default fallback

    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            new_address = form.save(commit=False)
            new_address.user = request.user
            new_address.save()

            # redirect after saving
            if next_page == "checkout":
                return redirect("checkout:checkout")
            else:
                return redirect("user_addresses:address_list")
    else:
        form = AddressForm()

    return render(request, "user_addresses/address_form.html", {
        "form": form,
        "next": next_page
    })



@login_required
def address_edit(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)

    next_page = request.GET.get("next", "address_list")  # fallback to address list

    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, "Address updated successfully.")

            # redirect after save
            if next_page == "checkout":
                return redirect("checkout:checkout_page")
            else:
                return redirect("user_addresses:address_list")

    else:
        form = AddressForm(instance=address)

    return render(request, "user_addresses/address_form.html", {
        "form": form,
        "next": next_page,
    })




@login_required
def address_delete(request, pk):
    profile = Profile.objects.get(user=request.user)
    address = get_object_or_404(Address, pk=pk, user=request.user)
    
    if request.method == 'POST':
        address.is_deleted = True
        address.save()
        messages.success(request, "Address deleted successfully.")
        return redirect('user_addresses:address_list')
    return render(request, 'user_addresses/address_confirm_delete.html', {
        'address': address,
        'profile': profile 
    })