from django.urls import path
from . import views

app_name = 'category_management'

urlpatterns = [
    path('', views.category_list, name='category_list'),
    path('add/', views.category_create, name='category_create'),
    path('edit/<int:pk>/', views.category_edit, name='category_edit'),
    path('delete/<int:pk>/', views.category_delete_confirm, name='category_delete_confirm'),
    path('toggle/<int:category_id>/', views.category_toggle, name='category_toggle'),
]
