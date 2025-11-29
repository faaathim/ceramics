from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('<str:order_id>/', views.order_detail, name='order_detail'),
    path('<str:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('<str:order_id>/return/', views.return_order, name='return_order'),
    path('<str:order_id>/invoice/', views.download_invoice, name='download_invoice'),
]
