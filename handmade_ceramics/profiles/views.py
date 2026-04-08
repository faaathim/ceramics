from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import logout
from datetime import timedelta
import base64, sys
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

from .models import Profile, EmailChangeOTP, Address
from .forms import ProfileForm, ChangePasswordForm, AddressForm


def process_cropped_image(request):
    cropped_data = request.POST.get("cropped_image")
    if not cropped_data:
        return None

    format_part, imgstr = cropped_data.split(";base64,")
    ext = format_part.split("/")[-1].lower()

    image_data = base64.b64decode(imgstr)
    file_buffer = BytesIO(image_data)

    return InMemoryUploadedFile(
        file_buffer,
        field_name="profile_image",
        name=f"profile_{request.user.id}.{ext}",
        content_type=f"image/{ext}",
        size=sys.getsizeof(file_buffer),
        charset=None,
    )


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, 'profiles/profile/profile_view.html', {'profile': profile})

@login_required
def profile_edit(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        image_file = process_cropped_image(request)
        files = request.FILES.copy()
        if image_file:
            files['profile_image'] = image_file

        form = ProfileForm(request.POST, files, instance=profile, user=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profiles:profile_view')
    else:
        form = ProfileForm(instance=profile, user=request.user)

    return render(request, 'profiles/profile/profile_edit.html', {'form': form})


@login_required
def change_password(request):
    if request.method == "POST":
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data["new_password"])
            request.user.save()
            logout(request)
            return redirect("user_authentication:login")
    else:
        form = ChangePasswordForm(request.user)

    return render(request, "profiles/profile/change_password.html", {"form": form})


# ADDRESS VIEWS

@login_required
def address_list(request):
    profile = Profile.objects.get(user=request.user)
    addresses = Address.objects.filter(user=request.user, is_deleted=False)
    return render(request, 'profiles/address/address_list.html', {
        'addresses': addresses,
        'profile': profile
    })


@login_required
def address_add(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            return redirect('profiles:address_list')
    else:
        form = AddressForm()

    return render(request, "profiles/address/address_form.html", {"form": form})


@login_required
def address_edit(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)

    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            return redirect('profiles:address_list')
    else:
        form = AddressForm(instance=address)

    return render(request, "profiles/address/address_form.html", {"form": form})


@login_required
def address_delete(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)

    if request.method == 'POST':
        address.is_deleted = True
        address.save()
        return redirect('profiles:address_list')

    return render(request, 'profiles/address/address_confirm_delete.html', {
        'address': address
    })