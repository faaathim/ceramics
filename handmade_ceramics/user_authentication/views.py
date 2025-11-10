from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone 
from datetime import timezone as dt_timezone  
from django.conf import settings
from django.contrib.auth import get_user_model, login, authenticate, logout
from django.core.mail import send_mail
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User

from .forms import SignupForm, OTPForm, LoginForm, ForgotPasswordForm, VerifyOTPForm, ResetPasswordForm
from .models import OTP, PasswordResetOTP

import datetime
import random

User = get_user_model()

OTP_EXPIRY_SECONDS = 60        
OTP_RESEND_COOLDOWN = 60          
MAX_OTP_ATTEMPTS = 5              

def _send_otp_email(user_email, code):
    subject = "Your Handmade Ceramics Signup OTP"
    message = f"Your 4-digit OTP is: {code}\nIt is valid for 69 seconds."
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient = [user_email]
    send_mail(subject, message, from_email, recipient)


@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['email'], 
                email=form.cleaned_data['email'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data.get('last_name', ''),
                password=form.cleaned_data['password1'],
                is_active=False
            )
            otp = OTP.generate_otp(user)
            _send_otp_email(user.email, otp.code)

            request.session['signup_user_id'] = user.id
            request.session['otp_sent_at'] = otp.created_at.timestamp()

            return redirect(reverse('user_authentication:verify_otp'))
    else:
        form = SignupForm()
    return render(request, 'user_authentication/signup.html', {'form': form})


@require_http_methods(["GET", "POST"])
def verify_otp_view(request):
    user_id = request.session.get('signup_user_id')
    if not user_id:
        messages.error(request, "No signup in progress. Please sign up first.")
        return redirect(reverse('user_authentication:signup'))

    user = get_object_or_404(User, pk=user_id)
    form = OTPForm(request.POST or None)
    otp_sent_at_ts = request.session.get('otp_sent_at', None)
    otp_sent_at = datetime.datetime.fromtimestamp(otp_sent_at_ts, tz=dt_timezone.utc) if otp_sent_at_ts else None

    if request.method == 'POST' and form.is_valid():
        code = form.cleaned_data['code']
        otp_qs = OTP.objects.filter(user=user, is_used=False).order_by('-created_at')
        if not otp_qs.exists():
            messages.error(request, "No OTP found. Please resend OTP.")
            return redirect(reverse('user_authentication:verify_otp'))
        otp = otp_qs.first()

        age = (timezone.now() - otp.created_at).total_seconds()
        if age > OTP_EXPIRY_SECONDS:
            messages.error(request, "OTP expired. Please resend.")
            return redirect(reverse('user_authentication:verify_otp'))

        if otp.attempts >= MAX_OTP_ATTEMPTS:
            messages.error(request, "Too many invalid attempts. OTP invalidated. Please resend.")
            otp.is_used = True
            otp.save()
            return redirect(reverse('user_authentication:verify_otp'))

        if otp.code != code:
            otp.attempts += 1
            otp.save()
            messages.error(request, "Invalid code. Please try again.")
            return redirect(reverse('user_authentication:verify_otp'))

        otp.is_used = True
        otp.save()
        user.is_active = True
        user.save()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        request.session.pop('signup_user_id', None)
        request.session.pop('otp_sent_at', None)
        messages.success(request, "Signup complete — welcome!")
        return redirect('user_side:home')  
    seconds_left = 0
    if otp_sent_at:
        elapsed = (timezone.now() - otp_sent_at).total_seconds()
        seconds_left = max(0, OTP_RESEND_COOLDOWN - int(elapsed))
    return render(request, 'user_authentication/verify_otp.html', {
        'form': form,
        'seconds_left': seconds_left,
        'resend_allowed': seconds_left == 0
    })


@require_http_methods(["POST"])
def resend_otp_view(request):
    user_id = request.session.get('signup_user_id')
    if not user_id:
        messages.error(request, "No signup in progress.")
        return redirect(reverse('user_authentication:signup'))
    user = get_object_or_404(User, pk=user_id)

    last_otp = OTP.objects.filter(user=user).order_by('-created_at').first()
    if last_otp:
        age = (timezone.now() - last_otp.created_at).total_seconds()
        if age < OTP_RESEND_COOLDOWN:
            messages.error(request, f"Please wait {int(OTP_RESEND_COOLDOWN - age)} seconds before resending.")
            return redirect(reverse('user_authentication:verify_otp'))
        OTP.objects.filter(user=user, is_used=False).update(is_used=True)

    new_otp = OTP.generate_otp(user)
    _send_otp_email(user.email, new_otp.code)
    request.session['otp_sent_at'] = new_otp.created_at.timestamp()
    messages.success(request, "A new OTP has been sent.")
    return redirect(reverse('user_authentication:verify_otp'))

def user_login(request):
    if request.user.is_authenticated:
        # already logged in
        return redirect('user_side:home')

    form = LoginForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me')

            # Authenticate user using username (since Django uses username field by default)
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, "Invalid email or password.")
                return redirect('user_authentication:login')

            user = authenticate(username=user.username, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)
                    # Control session expiry
                    if remember_me:
                        request.session.set_expiry(60 * 60 * 24 * 7)  # 7 days
                    else:
                        request.session.set_expiry(0)  # session ends on browser close

                    messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                    return redirect('user_side:home')
                else:
                    messages.warning(request, "Your account is inactive. Please contact support.")
            else:
                messages.error(request, "Invalid email or password.")
        else:
            messages.error(request, "Please correct the errors below.")

    context = {'form': form}
    return render(request, 'user_authentication/login.html', context)


def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('user_authentication:login')


def forgot_password(request):
    """Step 1: Enter email, send OTP"""
    form = ForgotPasswordForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, "No account found with this email.")
                return redirect('user_authentication:forgot_password')

            # Generate OTP (4 digits)
            otp = str(random.randint(1000, 9999))
            PasswordResetOTP.objects.create(user=user, otp=otp)

            # Send email
            send_mail(
                subject='Your Password Reset OTP',
                message=f'Your OTP for password reset is: {otp}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

            # Save user id in session
            request.session['reset_user_id'] = user.id
            messages.success(request, "OTP sent to your email.")
            return redirect('user_authentication:verify_otp')
    return render(request, 'user_authentication/forgot_password.html', {'form': form})


def verify_otp(request):
    """Step 2: Verify OTP"""
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, "Session expired. Please try again.")
        return redirect('user_authentication:forgot_password')

    form = VerifyOTPForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            otp_input = form.cleaned_data['otp']
            user = User.objects.get(id=user_id)

            otp_obj = PasswordResetOTP.objects.filter(user=user, otp=otp_input, is_used=False).order_by('-created_at').first()

            if otp_obj and otp_obj.is_valid():
                otp_obj.is_used = True
                otp_obj.save()
                request.session['otp_verified'] = True
                messages.success(request, "OTP verified successfully.")
                return redirect('user_authentication:reset_password')
            else:
                messages.error(request, "Invalid or expired OTP.")
    return render(request, 'user_authentication/otp_forgot.html', {'form': form})


def reset_password(request):
    """Step 3: Reset password after OTP verification"""
    user_id = request.session.get('reset_user_id')
    otp_verified = request.session.get('otp_verified')

    if not user_id or not otp_verified:
        messages.error(request, "Unauthorized access.")
        return redirect('user_authentication:forgot_password')

    form = ResetPasswordForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user = User.objects.get(id=user_id)
            user.set_password(new_password)
            user.save()

            # clear session
            request.session.pop('reset_user_id', None)
            request.session.pop('otp_verified', None)

            messages.success(request, "Password reset successfully! Please log in.")
            return redirect('user_authentication:login')
    return render(request, 'user_authentication/reset_password.html', {'form': form})