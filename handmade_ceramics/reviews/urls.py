from django.urls import path
from . import views

app_name = "review"

urlpatterns = [
    path('add/<int:product_id>/', views.add_review, name='add_review'),
]