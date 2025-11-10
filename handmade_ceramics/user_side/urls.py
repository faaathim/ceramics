# user_side/urls.py
from django.urls import path
from . import views

app_name = 'user_side'

urlpatterns = [
    path('', views.home, name='home'), 
    path('shop/', views.shop, name='shop'),
]
