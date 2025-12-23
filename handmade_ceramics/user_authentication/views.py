from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.contrib.auth import (
    get_user_model, login, authenticate, logout
)
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache

from .forms import SignupForm, OTPForm, LoginForm,ForgotPasswordForm
from .models import OTP
from django.http import JsonResponse


User = get_user_model()


# -------------------------------------------------
# Helper: Send OTP Email
# -------------------------------------------------

def send_otp_email(email, code):
    subject = "Your OTP Code"
    message = (
        f"Your 4-digit OTP is: {code}\n"
        f"This OTP is valid for 60seconds"
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )


# -------------------------------------------------
# SIGNUP
# -------------------------------------------------

@never_cache
@require_http_methods(["GET", "POST"])
def signup_view(request):
    form = SignupForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = User.objects.create_user(
            username=form.cleaned_data["email"],
            email=form.cleaned_data["email"],
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data.get("last_name", ""),
            password=form.cleaned_data["password1"],
            is_active=False,  # activate after OTP
        )

        otp_code = OTP.generate_otp()
        OTP.objects.create(
            user=user,
            code=otp_code,
            purpose="signup"
        )

        send_otp_email(user.email, otp_code)
        request.session["verify_user_id"] = user.id

        messages.success(request, "OTP sent to your email.")
        return redirect("user_authentication:verify_signup_otp")

    return render(
        request,
        "user_authentication/signup.html",
        {"form": form},
    )

# -------------------------------------------------
# SIGNUP OTP VERIFY
# -------------------------------------------------

@never_cache
@require_http_methods(["GET", "POST"])
def verify_signup_otp(request):
    user_id = request.session.get("verify_user_id")

    if not user_id:
        messages.error(request, "Signup session expired.")
        return redirect("user_authentication:signup")

    user = get_object_or_404(User, id=user_id)
    form = OTPForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        otp = OTP.objects.filter(
            user=user,
            code=form.cleaned_data["code"],
            purpose="signup",
            is_used=False
        ).last()

        if not otp or otp.is_expired():
            messages.error(request, "Invalid or expired OTP.")
            return redirect("user_authentication:verify_signup_otp")

        otp.is_used = True
        otp.save()

        user.is_active = True
        user.save()

        # ✅ IMPORTANT FIX
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        request.session.pop("verify_user_id", None)

        messages.success(request, "Account verified successfully!")
        return redirect("user_side:home")

    return render(
        request,
        "user_authentication/verify_otp.html",
        {"form": form},
    )



# -------------------------------------------------
# LOGIN
# -------------------------------------------------

@never_cache
@require_http_methods(["GET", "POST"])
def user_login(request):
    if request.user.is_authenticated:
        return redirect("user_side:home")

    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        remember_me = form.cleaned_data.get("remember_me")

        try:
            user_obj = User.objects.get(email__iexact=email)  # case-insensitive
        except User.DoesNotExist:
            messages.error(request, "Invalid credentials.")  # avoid email enumeration
            return redirect("user_authentication:login")

        user = authenticate(request, username=user_obj.username, password=password)
        if not user:
            messages.error(request, "Invalid credentials.")
            return redirect("user_authentication:login")


        login(request, user)

        if remember_me:
            request.session.set_expiry(60 * 60 * 24 * 7)  # 7 days
        else:
            request.session.set_expiry(0)

        messages.success(request, "Welcome back!")
        return redirect("user_side:home")

    return render(
        request,
        "user_authentication/login.html",
        {"form": form},
    )


# -------------------------------------------------
# LOGOUT
# -------------------------------------------------

@never_cache
def user_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("user_authentication:login")


# -------------------------------------------------
# FORGOT PASSWORD (SEND OTP)
# -------------------------------------------------

@never_cache
@require_http_methods(["GET", "POST"])
def forgot_password(request):
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                messages.success(
                    request,
                    "If this email exists, an OTP has been sent."
                )
                return redirect("user_authentication:forgot_password")

            OTP.objects.filter(
                user=user, purpose="reset", is_used=False
            ).update(is_used=True)

            otp_code = OTP.generate_otp()
            OTP.objects.create(user=user, code=otp_code, purpose="reset")
            send_otp_email(user.email, otp_code)

            request.session["reset_user_id"] = user.id
            messages.success(request, "OTP sent to your email.")
            return redirect("user_authentication:verify_reset_otp")
    else:
        form = ForgotPasswordForm()   # ✅ CREATE FORM FOR GET REQUEST

    return render(
        request,
        "user_authentication/forgot_password.html",
        {"form": form}                # ✅ PASS FORM TO TEMPLATE
    )



# -------------------------------------------------
# VERIFY RESET OTP
# -------------------------------------------------

@never_cache
@require_http_methods(["GET", "POST"])
def verify_reset_otp(request):
    user_id = request.session.get("reset_user_id")

    if not user_id:
        messages.error(request, "Session expired.")
        return redirect("user_authentication:forgot_password")

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        code = request.POST.get("code")

        otp = OTP.objects.filter(
            user=user,
            code=code,
            purpose="reset",
            is_used=False
        ).last()

        if not otp or otp.is_expired():
            messages.error(request, "Invalid or expired OTP.")
            return redirect("user_authentication:verify_reset_otp")

        otp.is_used = True
        otp.save()

        request.session["reset_verified"] = True
        messages.success(request, "OTP verified. Set a new password.")
        return redirect("user_authentication:reset_password")

    return render(request, "user_authentication/verify_reset_otp.html")


# -------------------------------------------------
# RESET PASSWORD
# -------------------------------------------------

@never_cache
@require_http_methods(["GET", "POST"])
def reset_password(request):
    user_id = request.session.get("reset_user_id")
    verified = request.session.get("reset_verified")

    if not user_id or not verified:
        messages.error(request, "Unauthorized access.")
        return redirect("user_authentication:forgot_password")

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("user_authentication:reset_password")

        try:
            validate_password(password1, user)
        except Exception as e:
            messages.error(request, e.messages[0])
            return redirect("user_authentication:reset_password")

        user.set_password(password1)
        user.save()

        request.session.pop("reset_user_id", None)
        request.session.pop("reset_verified", None)
        messages.success(request, "Password reset successfully.")
        return redirect("user_authentication:login")

    return render(request, "user_authentication/reset_password.html")


@never_cache
@require_http_methods(["GET", "POST"])
def resend_signup_otp(request):
    user_id = request.session.get("verify_user_id")

    if not user_id:
        messages.error(request, "Signup session expired.")
        return redirect("user_authentication:signup")

    user = get_object_or_404(User, id=user_id)

    OTP.objects.filter(
        user=user,
        purpose="signup",
        is_used=False
    ).update(is_used=True)

    otp_code = OTP.generate_otp()
    OTP.objects.create(
        user=user,
        code=otp_code,
        purpose="signup"
    )

    send_otp_email(user.email, otp_code)

    messages.success(request, "New OTP sent to your email.")
    return redirect("user_authentication:verify_signup_otp")


# -------------------------------------------------
# RESEND RESET OTP
# -------------------------------------------------

@never_cache
@require_http_methods(["POST"])
def resend_reset_otp(request):
    print("# 1. Get user ID from session")
    user_id = request.session.get("reset_user_id")

    print("# If session expired, stop here")
    if not user_id:
        return JsonResponse(
            {"error": "Session expired. Please try again."},
            status=400
        )

    print("# 2. Get user object")
    user = get_object_or_404(User, id=user_id)

    print("# 3. Invalidate any previous unused reset OTPs")
    OTP.objects.filter(
        user=user,
        purpose="reset",
        is_used=False
    ).update(is_used=True)

    print("# 4. Generate a new OTP")
    new_otp = OTP.generate_otp()

    print("# 5. Save new OTP in database")
    OTP.objects.create(
        user=user,
        code=new_otp,
        purpose="reset"
    )

    print("# 6. Send OTP to user's email")
    send_otp_email(user.email, new_otp)

    print("# 7. Optional success message (for frontend)")
    messages.success(request, "A new OTP has been sent to your email.")

    print("# 8. Return success response")
    return JsonResponse({"success": True})
