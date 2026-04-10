# user_authentication/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, login, authenticate, logout
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from .models import OTP
from .forms import SignupForm, OTPForm, LoginForm, ResetPasswordForm

User = get_user_model()
OTP_EXPIRY_SECONDS = 180


def create_and_send_otp(email, purpose, user=None, first_name=""):
    last_otp = OTP.objects.filter(email=email, purpose=purpose).last()

    # Prevent spam (30 sec cooldown)
    if last_otp and (timezone.now() - last_otp.created_at).total_seconds() < 30:
        raise Exception("Please wait before requesting another OTP.")

    OTP.objects.filter(email=email, purpose=purpose, is_used=False).update(is_used=True)

    otp_code = OTP.generate_otp()
    hashed_code = OTP.hash_otp(otp_code)

    OTP.objects.create(
        user=user,
        email=email,
        code_hash=hashed_code,
        purpose=purpose,
    )

    try:
        subject = "Your Verification Code"
        text_content = f"Hi {first_name}, Your OTP is: {otp_code}"

        email_msg = EmailMultiAlternatives(
            subject,
            text_content,
            settings.EMAIL_HOST_USER,
            [email],
        )
        email_msg.send()
    except Exception as e:
        print(f"EMAIL ERROR: {e}")
        print(f"OTP (DEV ONLY): {otp_code}")


def signup_view(request):
    form = SignupForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            request.session['signup_data'] = {
                'email': form.cleaned_data['email'],
                'password': form.cleaned_data['password1'],
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data.get('last_name', ''),
            }

            try:
                create_and_send_otp(
                    email=form.cleaned_data['email'],
                    purpose='signup',
                    first_name=form.cleaned_data['first_name']
                )
            except Exception as e:
                messages.error(request, str(e))
                return redirect('user_authentication:signup')

            return redirect('user_authentication:verify_otp')
        else:
            messages.error(request, "Please correct the errors below.")

    return render(request, 'user_authentication/signup.html', {'form': form})


def verify_otp(request):
    signup_data = request.session.get('signup_data')
    if not signup_data:
        messages.error(request, "Session expired. Please sign up again.")
        return redirect('user_authentication:signup')

    email = signup_data['email']
    otp = OTP.objects.filter(email=email, purpose='signup', is_used=False).last()

    remaining = 0
    if otp and not otp.is_expired():
        elapsed = (timezone.now() - otp.created_at).total_seconds()
        remaining = max(0, int(OTP_EXPIRY_SECONDS - elapsed))

    return render(request, 'user_authentication/verify_otp.html', {
        'form': OTPForm(), 
        'remaining_time': remaining
    })


@require_POST
def ajax_verify_signup_otp(request):
    signup_data = request.session.get('signup_data')

    if not signup_data:
        return JsonResponse({'error': 'Session expired.'}, status=400)

    code = request.POST.get('code', '').strip()

    otp = OTP.objects.filter(
        email=signup_data['email'],
        purpose='signup',
        is_used=False
    ).last()

    if not otp:
        return JsonResponse({'error': 'Invalid request.'}, status=400)

    if otp.is_expired():
        return JsonResponse({'error': 'OTP expired.'}, status=400)

    if otp.attempts >= OTP.MAX_ATTEMPTS:
        return JsonResponse({'error': 'Too many attempts. Request new OTP.'}, status=400)

    if not otp.verify(code):
        otp.attempts += 1
        otp.save()
        return JsonResponse({'error': 'Incorrect OTP.'}, status=400)

    otp.is_used = True
    otp.save()

    user = User.objects.create_user(
        username=signup_data['email'],
        email=signup_data['email'],
        password=signup_data['password'],
        first_name=signup_data['first_name'],
        last_name=signup_data['last_name']
    )

    login(request, user)
    request.session.flush()

    return JsonResponse({'success': True})


@require_POST
def ajax_resend_signup_otp(request):
    signup_data = request.session.get('signup_data')
    if not signup_data:
        return JsonResponse({'error': 'Session expired.'}, status=400)

    create_and_send_otp(
        email=signup_data['email'],
        purpose='signup',
        first_name=signup_data['first_name']
    )
    return JsonResponse({'success': True, 'expiry': OTP_EXPIRY_SECONDS})


def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user = User.objects.filter(email=email).first()
        if user:
            request.session['reset_email'] = email
            request.session['otp_verified_for_reset'] = False
            create_and_send_otp(
                email=email, 
                purpose='reset', 
                user=user, 
                first_name=user.first_name
            )
            return redirect('user_authentication:verify_reset_otp')
        messages.error(request, "No account found with that email.")
    return render(request, 'user_authentication/forgot_password.html')


def verify_reset_otp(request):
    if not request.session.get('reset_email'):
        return redirect('user_authentication:forgot_password')
    return render(request, 'user_authentication/verify_reset_otp.html')

@require_POST
def ajax_verify_reset_otp(request):
    email = request.session.get('reset_email')
    code = request.POST.get('code', '').strip()

    otp = OTP.objects.filter(email=email, purpose='reset', is_used=False).last()

    if not otp:
        return JsonResponse({'error': 'Invalid request.'}, status=400)

    if otp.is_expired():
        return JsonResponse({'error': 'OTP expired.'}, status=400)

    if otp.attempts >= OTP.MAX_ATTEMPTS:
        return JsonResponse({'error': 'Too many attempts.'}, status=400)

    if not otp.verify(code):
        otp.attempts += 1
        otp.save()
        return JsonResponse({'error': 'Invalid code.'}, status=400)

    otp.is_used = True
    otp.save()

    request.session['otp_verified_for_reset'] = True

    return JsonResponse({'success': True})


@require_POST
def ajax_resend_reset_otp(request):
    email = request.session.get('reset_email')
    user = User.objects.filter(email=email).first()
    if email:
        create_and_send_otp(email=email, purpose='reset', user=user, first_name=user.first_name if user else "")
        return JsonResponse({'success': True, 'expiry': OTP_EXPIRY_SECONDS})
    return JsonResponse({'error': 'Session error.'}, status=400)


def reset_password(request):
    if not request.session.get('otp_verified_for_reset'):
        messages.error(request, "Please verify OTP first.")
        return redirect('user_authentication:forgot_password')

    email = request.session.get('reset_email')
    user = User.objects.get(email=email)
    form = ResetPasswordForm(request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        user.set_password(form.cleaned_data['password1'])
        user.save()
        request.session.flush()
        messages.success(request, "Password reset successfully.")
        return redirect('user_authentication:login')
    return render(request, 'user_authentication/reset.html', {'form': form})


def login_view(request):
    form = LoginForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            user = authenticate(request, username=email, password=password)

            if user:
                login(request, user)
                return redirect('user_side:home')

            messages.error(request, "Invalid email or password.")
        else:
            messages.error(request, "Invalid input.")

    return render(request, 'user_authentication/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('user_authentication:login')