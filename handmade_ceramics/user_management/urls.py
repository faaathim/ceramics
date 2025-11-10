from django.urls import path
from . import views

app_name = 'user_management'

urlpatterns = [
    path('', views.user_list, name='user_list'),
    path('toggle/<int:user_id>/', views.confirm_toggle, name='confirm_toggle'),
]
