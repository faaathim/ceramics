from django.shortcuts import render, redirect, get_object_or_404

from django.http import HttpResponse

from user_auth.forms import SignUpForm
import random
from django.core.mail import send_mail
from django.conf import settings
from user_auth.models import User

from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.hashers import make_password
from django.views.decorators.cache import never_cache


# Create your views here.

User = get_user_model()



def home_view(request):
    return HttpResponse("Welcome to ceramics shop")


# user signup

@never_cache
def signup_view(request):
    if request.method == 'POST':
        print("request method is post")
        form = SignUpForm(request.POST)
        if form.is_valid():
            print("form is valid")
            user = form.save(commit=False)
            user.is_active = False
            otp = str(random.randint(1000, 9999))
            user.otp = otp 
            user.save()

            send_mail(
                subject="Your Ceramic Store OTP",
                message=f"Hello {user.username}, your OTP is {otp}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
            print("mail sent")
            request.session['pending_user_id'] = user.id


            return redirect('verify_otp')
        else:
            return render(request, 'user_auth/signup.html', {'form': form})
    else:
        form = SignUpForm()

    return render(request, 'user_auth/signup.html', {'form': form})


# OTP verification

@never_cache
def verify_otp_view(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        user_id = request.session.get('pending_user_id')
        if not user_id:
            user_id = request.session.get('reset_user_id')
        user = get_object_or_404(User, id=user_id)

        if user.otp == entered_otp:
            user.is_blocked = False
            user.is_active = True
            user.otp = None
            user.save()
            return redirect('login')
        else:
            return render(request, 'user_auth/verify_otp.html', {'error': 'Invalid OTP'})
    
    return render(request, 'user_auth/verify_otp.html')


# resend otp 

def resend_otp_view(request):
    user_id = request.session.get('pending_user_id')
    if not user_id:
        user_id = request.session.get('reset_user_id')
    user = get_object_or_404(User, id=user_id)

    otp = str(random.randint(1000, 9999))
    user.otp = otp
    user.save()

    send_mail(
        subject="Your Ceramic Store OTP (Resent)",
        message=f"Hello {user.username}, your new OTP is {otp}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )

    return redirect('verify_otp')


# user login

@never_cache
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_blocked:
                login(request, user)
                return redirect('home')
            else: 
                messages.error(request, 'Your account is blocked.')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'user_auth/login.html')


# logout

def logout_view(request):
    logout(request)
    return redirect('login')


# forgot password

@never_cache
def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            otp = str(random.randint(1000, 9999))
            user.otp = otp
            user.save()

            send_mail(
                "Ceramic Store Password Resent OTP",
                f"Hi {user.username}, your OTP for password reset is: {otp}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )

            request.session['reset_user_id'] = user.id
            return redirect('verify_reset_otp')
        except User.DoesNotExist:
            messages.error(request, "No user found with that email.")

    return render(request, 'user_auth/forgot_password.html')


# OTP verification view

@never_cache
def verify_reset_otp_view(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        user_id = request.session.get('reset_user_id')
        user = get_object_or_404(User, id=user_id)

        if user.otp == entered_otp:
            user.otp = None
            user.save()
            request.session['allow_password_reset'] = True
            return redirect('reset_password')
        else:
            messages.error(request, "Invalid OTP")
    
    return render(request, 'user_auth/verify_otp.html')


# reset password view 

@never_cache
def reset_password_view(request):
    if not request.session.get('allow_password_reset'):
        return redirect('login')
    
    user_id = request.session.get('reset_user_id')
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')

        if password != confirm:
            messages.error(request, "Passwords do not match.")
        else:
            user.password = make_password(password)
            user.save()
            del request.session['allow_password_reset']
            del request.session['reset_user_id']
            messages.success(request, "Password reset successfully.")
            return redirect('login')
        
    return render(request, 'user_auth/reset_password.html')
