from django.urls import path
from user_auth import views

urlpatterns = [
    path('', views.signup_view, name = 'signup'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),
    path('login/', views.login_view, name = 'login'),
    path('logout/', views.logout_view, name = 'logout'),
    path('forgot-password/', views.forgot_password_view, name="forgot_password"),
    path('verify-reset-otp/', views.verify_reset_otp_view, name="verify_reset_otp"),
    path('reset-password/', views.reset_password_view, name='reset_password'),
]