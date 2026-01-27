# payments/urls.py

from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("start/<str:order_id>/", views.start_payment, name="start"),
    path("verify/", views.verify_payment, name="verify"),  # optional now
    path("callback/", views.razorpay_callback, name="callback"),
    path("success/", views.payment_success, name="success"),
    path("failed/", views.payment_failed, name="failed"),
]

