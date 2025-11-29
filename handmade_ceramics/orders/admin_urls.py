# orders/admin_urls.py
from django.urls import path
from . import admin_views

app_name = 'orders_admin'

urlpatterns = [
    path('', admin_views.admin_order_list, name='admin_order_list'),
    path('<str:order_id>/', admin_views.admin_order_detail, name='admin_order_detail'),
    path('inventory/list/', admin_views.admin_inventory, name='admin_inventory'),
]
