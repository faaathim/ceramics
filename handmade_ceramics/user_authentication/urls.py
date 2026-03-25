from django.urls import path
from . import views

app_name = "user_authentication"

urlpatterns = [
    # Signup + OTP
    path('signup/',                    views.signup_view,             name='signup'),
    path('verify-otp/',                views.verify_otp,              name='verify_otp'),
    path('ajax/verify-otp/',           views.ajax_verify_signup_otp,  name='ajax_verify_signup_otp'),
    path('ajax/resend-otp/',           views.ajax_resend_signup_otp,  name='ajax_resend_signup_otp'),

    # Login / Logout
    path('login/',                     views.login_view,              name='login'),
    path('logout/',                    views.logout_view,             name='logout'),

    # Password Reset Flow
    path('forgot-password/',           views.forgot_password_view,    name='forgot_password'),
    path('verify-reset-otp/',          views.verify_reset_otp,        name='verify_reset_otp'),
    path('reset-password/',            views.reset_password,          name='reset_password'),

    # AJAX Endpoints for Reset
    path('ajax/verify-reset-otp/',     views.ajax_verify_reset_otp,   name='ajax_verify_reset_otp'),
    path('ajax/resend-reset-otp/',     views.ajax_resend_reset_otp,   name='resend_reset_otp'),
]