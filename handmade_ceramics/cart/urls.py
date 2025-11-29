from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_page, name='cart_page'),
    path('add/', views.add_to_cart, name='add_to_cart'),
    path('item/<int:item_id>/remove/', views.remove_cart_item, name='remove_cart_item'),
    path('item/<int:item_id>/update/', views.update_quantity, name='update_quantity'),
]