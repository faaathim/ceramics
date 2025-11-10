from django.urls import path
from . import views

app_name = 'product_management'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('add/', views.product_create, name='product_create'),
    path('edit/<int:pk>/', views.product_edit, name='product_edit'),
    path('delete/<int:pk>/', views.product_delete_confirm, name='product_delete_confirm'),
    path('<int:pk>/', views.product_detail, name='product_detail'),
]
