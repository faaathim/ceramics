# wallet/admin_urls.py

from django.urls import path
from . import admin_views

app_name = 'wallet_admin'

urlpatterns = [
    path(
        'transactions/',
        admin_views.admin_wallet_transaction_list,
        name='admin_wallet_transaction_list'
    ),
    path(
        'transactions/<uuid:transaction_id>/',
        admin_views.admin_wallet_transaction_detail,
        name='admin_wallet_transaction_detail'
    ),
]