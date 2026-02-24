# custom_admin/urls.py

from django.urls import path, include
from . import views as ca_views

app_name = 'custom_admin'

urlpatterns = [
    path('', ca_views.dashboard_view, name='dashboard'),
    path('login/', ca_views.login_view, name='login'),
    path('logout/', ca_views.logout_view, name='logout'),

    path('', ca_views.dashboard_view, name='dashboard'),
    path('dashboard/chart-data/', ca_views.dashboard_chart_data, name='chart_data'),
    path('dashboard/top-products/', ca_views.top_products_data, name='top_products'),
    path('dashboard/top-categories/', ca_views.top_categories_data, name='top_categories'),

    # user_management
    path('users/', include('user_management.urls', namespace='user_management')),

    # category_management
    path(
        'categories/',
        include(('category_management.urls', 'category_management'),
        namespace='category_management')
    ),

    # product_management
    path('products/', include('product_management.urls', namespace='product_management')),

    #orders
    path('orders/', include('orders.admin_urls', namespace='orders_admin')),

    # coupons
path(
    'coupons/',
    include(('coupons.admin_urls', 'coupons'),
    namespace='coupons')
),

    # offers 
    # ✅ CORRECT
path(
    'offers/',
    include(('offers.admin_urls', 'offers'), namespace='offers')
),

path(
    'wallet/',
    include('wallet.admin_urls', namespace='wallet_admin')
),

]
