from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model, login, authenticate, logout
from django.core.mail import send_mail
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache

from .forms import (
    SignupForm, OTPForm, LoginForm, ForgotPasswordForm,
    VerifyOTPForm, ResetPasswordForm
)
from .models import OTP, PasswordResetOTP

import random
from datetime import datetime, timezone as dt_timezone

User = get_user_model()

# OTP Config
OTP_EXPIRY_SECONDS = 60
OTP_RESEND_COOLDOWN = 60
MAX_OTP_ATTEMPTS = 5


# -----------------------------------------------
# Helper function to send OTP email
# -----------------------------------------------

def _send_otp_email(user_email, code):
    subject = "Your OTP Code"
    message = f"Your 4-digit OTP is: {code}\nIt is valid for {OTP_EXPIRY_SECONDS} seconds."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email])


# -----------------------------------------------
# SIGNUP
# -----------------------------------------------

@never_cache
@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():

            # Save user data temporarily in session
            request.session["temp_user"] = {
                "email": form.cleaned_data["email"],
                "first_name": form.cleaned_data["first_name"],
                "last_name": form.cleaned_data.get("last_name", ""),
                "password": form.cleaned_data["password1"],
            }

            # Generate a simple 4-digit OTP
            import random
            otp_code = str(random.randint(1000, 9999))

            # Store OTP in session
            request.session["signup_otp"] = otp_code
            request.session["otp_sent_at"] = timezone.now().timestamp()

            # Send OTP email
            _send_otp_email(form.cleaned_data["email"], otp_code)

            return redirect("user_authentication:verify_signup_otp")
    else:
        form = SignupForm()

    return render(request, "user_authentication/signup.html", {"form": form})


# -----------------------------------------------
# SIGNUP OTP VERIFY
# -----------------------------------------------

@never_cache
@require_http_methods(["GET", "POST"])
def verify_signup_otp(request):
    temp_user = request.session.get("temp_user")
    real_otp = request.session.get("signup_otp")

    if not temp_user:
        messages.error(request, "Signup expired. Please try again.")
        return redirect("user_authentication:signup")

    form = OTPForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        entered_otp = form.cleaned_data["code"]

        # Check OTP match
        if entered_otp != real_otp:
            messages.error(request, "Incorrect OTP.")
            return redirect("user_authentication:verify_signup_otp")

        # OTP correct → Create user now
        user = User.objects.create_user(
            username=temp_user["email"],
            email=temp_user["email"],
            first_name=temp_user["first_name"],
            last_name=temp_user["last_name"],
            password=temp_user["password"],
        )

        # Clear session
        request.session.pop("temp_user", None)
        request.session.pop("signup_otp", None)

        # Login user
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        messages.success(request, "Signup successful!")
        return redirect("user_side:home")

    return render(request, "user_authentication/verify_otp.html", {"form": form})


# -----------------------------------------------
# SIGNUP RESEND OTP
# -----------------------------------------------

@never_cache
@require_http_methods(["POST"])
def resend_signup_otp(request):
    user_id = request.session.get('signup_user_id')
    if not user_id:
        messages.error(request, "No signup session.")
        return redirect('user_authentication:signup')

    user = get_object_or_404(User, pk=user_id)

    last_otp = OTP.objects.filter(user=user).order_by('-created_at').first()
    if last_otp:
        age = (timezone.now() - last_otp.created_at).total_seconds()
        if age < OTP_RESEND_COOLDOWN:
            messages.error(request, f"Wait {int(OTP_RESEND_COOLDOWN - age)} seconds.")
            return redirect('user_authentication:verify_signup_otp')

        OTP.objects.filter(user=user, is_used=False).update(is_used=True)

    new_otp = OTP.generate_otp(user)
    _send_otp_email(user.email, new_otp.code)
    request.session['otp_sent_at'] = new_otp.created_at.timestamp()

    messages.success(request, "New OTP sent.")
    return redirect('user_authentication:verify_signup_otp')


# -----------------------------------------------
# LOGIN
# -----------------------------------------------

@never_cache
def user_login(request):
    if request.user.is_authenticated:
        return redirect('user_side:home')

    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        remember_me = form.cleaned_data['remember_me']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Invalid credentials.")
            return redirect('user_authentication:login')

        user = authenticate(request, username=user.username, password=password)

        if not user:
            messages.error(request, "Invalid credentials.")
            return redirect('user_authentication:login')

        if not user.is_active:
            messages.error(request, "Your account is inactive.")
            return redirect('user_authentication:login')

        login(request, user)

        # Remember me
        request.session.set_expiry(60 * 60 * 24 * 7 if remember_me else 0)

        messages.success(request, "Welcome back!")
        return redirect('user_side:home')

    return render(request, 'user_authentication/login.html', {'form': form})


# -----------------------------------------------
# LOGOUT
# -----------------------------------------------

@never_cache
def user_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('user_authentication:login')


# -----------------------------------------------
# FORGOT PASSWORD
# -----------------------------------------------

@never_cache
def forgot_password(request):
    form = ForgotPasswordForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No account with this email.")
            return redirect('user_authentication:forgot_password')

        # Invalidate old OTPs
        PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)

        otp = str(random.randint(1000, 9999))
        PasswordResetOTP.objects.create(user=user, otp=otp)

        _send_otp_email(email, otp)

        request.session['reset_user_id'] = user.id
        request.session['reset_otp_sent_at'] = timezone.now().timestamp()

        messages.success(request, "OTP sent to your email.")
        return redirect('user_authentication:verify_reset_otp')

    return render(request, 'user_authentication/forgot_password.html', {'form': form})


# -----------------------------------------------
# VERIFY RESET OTP
# -----------------------------------------------

@never_cache
def verify_reset_otp(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, "Session expired.")
        return redirect('user_authentication:forgot_password')

    user = User.objects.get(id=user_id)
    form = VerifyOTPForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        entered_code = form.cleaned_data['code']

        otp = PasswordResetOTP.objects.filter(
            user=user, otp=entered_code, is_used=False
        ).order_by('-created_at').first()

        if not otp:
            messages.error(request, "Invalid OTP.")
            return redirect('user_authentication:verify_reset_otp')

        # Check expiry (60 sec)
        if (timezone.now() - otp.created_at).total_seconds() > OTP_EXPIRY_SECONDS:
            messages.error(request, "OTP expired.")
            return redirect('user_authentication:verify_reset_otp')

        otp.is_used = True
        otp.save()

        request.session['otp_verified'] = True

        messages.success(request, "OTP verified. Set new password.")
        return redirect('user_authentication:reset_password')

    return render(request, 'user_authentication/otp_forgot.html', {'form': form})


# -----------------------------------------------
# RESET PASSWORD
# -----------------------------------------------

@never_cache
def reset_password(request):
    user_id = request.session.get('reset_user_id')
    otp_verified = request.session.get('otp_verified')

    if not user_id or not otp_verified:
        messages.error(request, "Unauthorized.")
        return redirect('user_authentication:forgot_password')

    form = ResetPasswordForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        new_password = form.cleaned_data['new_password']
        user = User.objects.get(id=user_id)
        user.set_password(new_password)
        user.save()

        request.session.pop('reset_user_id', None)
        request.session.pop('otp_verified', None)

        messages.success(request, "Password reset successfully.")
        return redirect('user_authentication:login')

    return render(request, 'user_authentication/reset_password.html', {'form': form})
