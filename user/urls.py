from django.urls import path
from . import views

app_name = 'user'

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('profile_detail/', views.profile_detail, name='profile_detail'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
]
