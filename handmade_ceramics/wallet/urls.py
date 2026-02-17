# wallet/urls.py

from django.urls import path
from . import views

app_name = "wallet"

urlpatterns = [
    path("wallet_payment/<str:order_id>", views.wallet_payment, name="wallet_payment"),
    path("dashboard/", views.wallet_dashboard, name="dashboard"),

]

# wallet/urls.py

from django.urls import path
from . import views

app_name = "wallet"

urlpatterns = [
    path("wallet_payment/<str:order_id>", views.wallet_payment, name="wallet_payment"),
    path("dashboard/", views.wallet_dashboard, name="dashboard"),

]

