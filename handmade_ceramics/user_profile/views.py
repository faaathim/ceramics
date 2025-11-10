# user_profile/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from .forms import ProfileForm
from .models import Profile, EmailChangeOTP
from datetime import timedelta


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, 'user_profile/profile_view.html', {'profile': profile})


@login_required
def profile_edit(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            new_email = form.cleaned_data.get('email')
            if new_email != request.user.email:
                otp = EmailChangeOTP.generate_otp(request.user, new_email)
                send_mail(
                    "Verify Your New Email",
                    f"Your verification code is: {otp}",
                    settings.DEFAULT_FROM_EMAIL,
                    [new_email],
                    fail_silently=False
                )
                request.session['pending_email'] = new_email
                messages.info(request, "An OTP has been sent to your new email.")
                return redirect('user_profile:verify_email_otp')
            else:
                form.save()
                messages.success(request, "Profile updated successfully!")
                return redirect('user_profile:profile_view')
    else:
        form = ProfileForm(instance=profile, user=request.user)
    return render(request, 'user_profile/profile_edit.html', {'form': form})


@login_required
def verify_email_otp(request):
    new_email = request.session.get('pending_email')
    if not new_email:
        messages.error(request, "No pending email change found.")
        return redirect('user_profile:profile_edit')

    last_otp = EmailChangeOTP.objects.filter(user=request.user, new_email=new_email, is_used=False).last()
    if request.method == "POST":
        entered = request.POST.get('otp')
        if last_otp and last_otp.is_valid() and last_otp.otp == entered:
            user = request.user
            user.email = new_email
            user.save()
            last_otp.is_used = True
            last_otp.save()
            del request.session['pending_email']
            messages.success(request, "Email updated successfully!")
            return redirect('user_profile:profile_view')
        else:
            messages.error(request, "Invalid or expired OTP.")

    # calculate resend cooldown
    seconds_left = 0
    if last_otp:
        elapsed = (timezone.now() - last_otp.created_at).total_seconds()
        seconds_left = max(0, 60 - int(elapsed))

    return render(request, 'user_profile/verify_email_otp.html', {'email': new_email, 'seconds_left': seconds_left})


@login_required
def resend_email_otp(request):
    new_email = request.session.get('pending_email')
    if not new_email:
        messages.error(request, "No pending email change request.")
        return redirect('user_profile:profile_edit')

    last_otp = EmailChangeOTP.objects.filter(user=request.user, new_email=new_email).last()
    if last_otp and timezone.now() < last_otp.created_at + timedelta(seconds=60):
        messages.warning(request, "Please wait before resending.")
        return redirect('user_profile:verify_email_otp')

    otp = EmailChangeOTP.generate_otp(request.user, new_email)
    send_mail(
        "Resend Email Verification Code",
        f"Your verification code is: {otp}",
        settings.DEFAULT_FROM_EMAIL,
        [new_email],
        fail_silently=False
    )
    messages.success(request, "OTP resent successfully.")
    return redirect('user_profile:verify_email_otp')
