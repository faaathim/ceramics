from django.urls import path
from . import admin_views

app_name = 'offers'

urlpatterns = [

    # PRODUCT OFFERS
    path('product/', admin_views.product_offer_list, name='product_offer_list'),
    path('product/add/', admin_views.product_offer_create, name='product_offer_create'),
    path('product/edit/<int:offer_id>/', admin_views.product_offer_edit, name='product_offer_edit'),
    path('product/delete/<int:offer_id>/', admin_views.product_offer_delete, name='product_offer_delete'),
    path('product/toggle/<int:offer_id>/', admin_views.product_offer_toggle, name='product_offer_toggle'),

    # CATEGORY OFFERS
    path('category/', admin_views.category_offer_list, name='category_offer_list'),
    path('category/add/', admin_views.category_offer_create, name='category_offer_create'),
    path('category/edit/<int:offer_id>/', admin_views.category_offer_edit, name='category_offer_edit'),
    path('category/delete/<int:offer_id>/', admin_views.category_offer_delete, name='category_offer_delete'),
    path('category/toggle/<int:offer_id>/', admin_views.category_offer_toggle, name='category_offer_toggle'),
]
