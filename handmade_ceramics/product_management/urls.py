from django.urls import path
from . import views

app_name = 'product_management'

urlpatterns = [
    # Product management (Admin)
    path('', views.product_list, name='product_list'),
    path('add/', views.product_create, name='product_create'),
    path('<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('<int:pk>/toggle-listing/', views.product_toggle_listing, name='product_toggle_listing'),
    
    # Public product detail (with optional ?variant=<id>)
    path('product/<int:pk>/', views.product_detail, name='product_detail'),

    # Variant API for switching colors
    path('variant/api/<int:variant_id>/', views.variant_json, name='variant_json'),

    # Variant management (Admin)
    path('product/<int:product_pk>/variants/', views.variant_list, name='variant_list'),
    path('product/<int:product_pk>/variants/add/', views.variant_create, name='variant_create'),
    path('product/<int:product_pk>/variants/<int:pk>/edit/', views.variant_edit, name='variant_edit'),
    path('product/<int:product_pk>/variants/<int:pk>/delete/', views.variant_delete_confirm, name='variant_delete_confirm'),
    path('product/<int:product_pk>/variants/<int:pk>/toggle-listing/', views.variant_toggle_listing, name='variant_toggle_listing'),
]
from django.urls import path
from . import views

app_name = 'product_management'

urlpatterns = [
    # Product management (Admin)
    path('', views.product_list, name='product_list'),
    path('add/', views.product_create, name='product_create'),
    path('<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('<int:pk>/toggle-listing/', views.product_toggle_listing, name='product_toggle_listing'),
    
    # Public product detail (with optional ?variant=<id>)
    path('product/<int:pk>/', views.product_detail, name='product_detail'),

    # Variant API for switching colors
    path('variant/api/<int:variant_id>/', views.variant_json, name='variant_json'),

    # Variant management (Admin)
    path('product/<int:product_pk>/variants/', views.variant_list, name='variant_list'),
    path('product/<int:product_pk>/variants/add/', views.variant_create, name='variant_create'),
    path('product/<int:product_pk>/variants/<int:pk>/edit/', views.variant_edit, name='variant_edit'),
    path('product/<int:product_pk>/variants/<int:pk>/delete/', views.variant_delete_confirm, name='variant_delete_confirm'),
    path('product/<int:product_pk>/variants/<int:pk>/toggle-listing/', views.variant_toggle_listing, name='variant_toggle_listing'),
]
