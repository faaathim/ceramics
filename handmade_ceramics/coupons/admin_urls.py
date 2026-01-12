from django.urls import path
from . import admin_views

app_name = 'coupons'

urlpatterns = [
    path('', admin_views.coupon_list, name='coupon_list'),
    path('add/', admin_views.coupon_create, name='coupon_create'),
    path('edit/<int:coupon_id>/', admin_views.coupon_edit, name='coupon_edit'),
    path('delete/<int:coupon_id>/', admin_views.coupon_delete, name='coupon_delete'),
    path('toggle/<int:coupon_id>/', admin_views.coupon_toggle, name='coupon_toggle'),
]
