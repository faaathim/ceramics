# orders/urls.py

from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('<str:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('cancel-item/<str:order_id>/<int:item_id>/', views.cancel_order_item, name='cancel_order_item'),
    path('<str:order_id>/return/', views.return_order, name='return_order'),
    path('<str:order_id>/invoice/', views.download_invoice, name='download_invoice'),
    path('<str:order_id>/', views.order_detail, name='order_detail'),
    path('return-item/<int:item_id>/',views.request_item_return,name='request_item_return'),
]