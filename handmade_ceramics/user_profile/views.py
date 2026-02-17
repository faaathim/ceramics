from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model, logout
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from io import BytesIO
import base64
import sys
from datetime import timedelta
from django.core.files.base import ContentFile

from .forms import ProfileForm, ChangePasswordForm
from .models import Profile, EmailChangeOTP

User = get_user_model()


def process_cropped_image(request):
    """Convert base64 cropped image to ContentFile for CloudinaryField."""
    cropped_data = request.POST.get('cropped_image')
    if not cropped_data:
        return None

    if ';base64,' not in cropped_data:
        raise ValueError("Invalid image format")

    format_part, imgstr = cropped_data.split(';base64,')
    ext = format_part.split('/')[-1].lower()
    if ext not in ['jpeg', 'jpg', 'png']:
        raise ValueError("Only JPEG or PNG images are allowed")

    image_data = base64.b64decode(imgstr)
    return ContentFile(image_data, name=f'profile_{request.user.id}.{ext}')


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, 'user_profile/profile_view.html', {'profile': profile})


@login_required
def profile_edit(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        try:
            image_file = process_cropped_image(request)
            if image_file:
                request.FILES['profile_image'] = image_file  # Works with CloudinaryField
        except Exception as e:
            messages.error(request, f"Image error: {str(e)}")
            return redirect('user_profile:profile_edit')

        form = ProfileForm(request.POST, request.FILES, instance=profile, user=request.user)

        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    label = form.fields[field].label if field != '__all__' else ''
                    messages.error(request, f"{label}: {error}" if label else error)
            return render(request, 'user_profile/profile_edit.html', {'form': form, 'profile': profile})

        new_email = form.cleaned_data.get('email')

        if new_email and new_email.lower() != request.user.email.lower():
            if User.objects.filter(email__iexact=new_email).exclude(pk=request.user.pk).exists():
                form.add_error('email', "This email is already registered with another account.")
                messages.error(request, "This email is already registered with another account.")
                return render(request, 'user_profile/profile_edit.html', {'form': form, 'profile': profile})

            try:
                otp = EmailChangeOTP.generate_otp(request.user, new_email)
                send_mail(
                    "Verify Your New Email",
                    f"Your verification code is: {otp}\n\nThis code will expire in 5 minutes.",
                    settings.DEFAULT_FROM_EMAIL,
                    [new_email],
                )
                request.session['pending_email'] = new_email
                form.save(commit=False).save()
                messages.info(request, f"An OTP has been sent to {new_email}. Please verify it.")
                return redirect('user_profile:verify_email_otp')
            except Exception as e:
                messages.error(request, f"Failed to send verification email: {str(e)}")
                return redirect('user_profile:profile_edit')

        try:
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('user_profile:profile_view')
        except ValidationError as e:
            messages.error(request, ", ".join(e.messages))
        except Exception as e:
            messages.error(request, f"Could not save profile: {str(e)}")

    else:
        form = ProfileForm(instance=profile, user=request.user)

    return render(request, 'user_profile/profile_edit.html', {'form': form, 'profile': profile})


@login_required
def verify_email_otp(request):
    new_email = request.session.get('pending_email')
    if not new_email:
        messages.error(request, "No pending email change found.")
        return redirect('user_profile:profile_edit')

    last_otp = EmailChangeOTP.objects.filter(
        user=request.user, new_email=new_email, is_used=False
    ).order_by('-created_at').first()

    if request.method == "POST":
        entered = request.POST.get('otp', '').strip()

        if not entered:
            messages.error(request, "Please enter the OTP code.")
        elif last_otp and last_otp.is_valid() and last_otp.otp == entered:
            user = request.user
            user.email = new_email
            user.save()
            last_otp.is_used = True
            last_otp.save()
            del request.session['pending_email']
            messages.success(request, "Email updated successfully!")
            return redirect('user_profile:profile_view')
        else:
            if not last_otp:
                messages.error(request, "No OTP found. Please request a new one.")
            elif not last_otp.is_valid():
                messages.error(request, "OTP has expired. Please request a new one.")
            else:
                messages.error(request, "Invalid OTP. Please try again.")

    seconds_left = 0
    if last_otp:
        elapsed = (timezone.now() - last_otp.created_at).total_seconds()
        seconds_left = max(0, 60 - int(elapsed))

    return render(request, 'user_profile/verify_email_otp.html', {
        'email': new_email,
        'seconds_left': seconds_left
    })


@login_required
def resend_email_otp(request):
    new_email = request.session.get('pending_email')
    if not new_email:
        messages.error(request, "No pending email change request.")
        return redirect('user_profile:profile_edit')

    last_otp = EmailChangeOTP.objects.filter(user=request.user, new_email=new_email).order_by('-created_at').first()

    if last_otp and timezone.now() < last_otp.created_at + timedelta(seconds=60):
        remaining = 60 - int((timezone.now() - last_otp.created_at).total_seconds())
        messages.warning(request, f"Please wait {remaining} seconds before resending.")
        return redirect('user_profile:verify_email_otp')

    try:
        otp = EmailChangeOTP.generate_otp(request.user, new_email)
        send_mail(
            "Resend Email Verification Code",
            f"Your verification code is: {otp}\n\nThis code will expire in 5 minutes.",
            settings.DEFAULT_FROM_EMAIL,
            [new_email],
        )
        messages.success(request, "OTP resent successfully.")
    except Exception as e:
        messages.error(request, f"Failed to resend OTP: {str(e)}")

    return redirect('user_profile:verify_email_otp')


@login_required
def change_password(request):
    if request.method == "POST":
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            user = request.user
            user.set_password(form.cleaned_data["new_password"])
            user.save()
            messages.success(request, "Your password has been updated successfully. Please log in again.")
            logout(request)
            return redirect("user_authentication:login")
        for error in form.errors.values():
            messages.error(request, error)
    else:
        form = ChangePasswordForm(request.user)

    return render(request, "user_profile/change_password.html", {"form": form})
