# user_profile/urls.py
from django.urls import path
from . import views

app_name = 'user_profile'

urlpatterns = [
    path('', views.profile_view, name='profile_view'),
    path('edit/', views.profile_edit, name='profile_edit'),
    path('change-password/', views.change_password, name='change_password'),
    path('verify-email/', views.verify_email_otp, name='verify_email_otp'),
    path('resend-email-otp/', views.resend_email_otp, name='resend_email_otp'),
]
