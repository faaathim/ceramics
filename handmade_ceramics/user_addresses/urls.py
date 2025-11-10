from django.urls import path
from . import views

app_name = 'user_addresses'

urlpatterns = [
    path('', views.address_list, name='address_list'),
    path('add/', views.address_add, name='address_add'),
    path('<int:pk>/edit/', views.address_edit, name='address_edit'),
    path('<int:pk>/delete/', views.address_delete, name='address_delete'),
]
