# custom_admin/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import AdminLoginForm
from django.http import JsonResponse
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.contrib.auth import get_user_model

from orders.models import Order, OrderItem
from category_management.models import Category


def superuser_check(user):
    return user.is_active and user.is_superuser


def login_view(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('custom_admin:dashboard')

    form = AdminLoginForm(request=request, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        if user.is_superuser:
            login(request, user)
            messages.success(
                request,
                f"Welcome back, {user.get_full_name() or user.username}!"
            )
            return redirect('custom_admin:dashboard')
        else:
            messages.error(request, "Access denied. Admin privileges required.")
    elif request.method == 'POST':
        messages.error(request, "Invalid username or password.")

    return render(request, 'custom_admin/login.html', {'form': form})


@login_required(login_url='custom_admin:login')
def logout_view(request):
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('custom_admin:login')


@user_passes_test(superuser_check, login_url='custom_admin:login')
@login_required(login_url='custom_admin:login')
def dashboard_view(request):
    User = get_user_model()

    total_users = User.objects.filter(is_superuser=False).count()
    total_orders = Order.objects.count()
    total_sales = Order.objects.filter(
        status='DELIVERED'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    total_pending = Order.objects.filter(status='PENDING').count()

    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
        'total_users': total_users,
        'total_orders': total_orders,
        'total_sales': total_sales,
        'total_pending': total_pending,
    }

    return render(request, 'custom_admin/dashboard.html', context)



@user_passes_test(superuser_check, login_url='custom_admin:login')
@login_required(login_url='custom_admin:login')
def dashboard_chart_data(request):
    current_year = timezone.now().year

    orders = (Order.objects
              .filter(status='DELIVERED', created_at__year=current_year)
              .annotate(month=TruncMonth('created_at'))
              .values('month')
              .annotate(revenue=Sum('total_amount'), order_count=Count('id'))
              .order_by('month')
              )
    labels = []
    revenue_data = []
    order_data = []

    for entry in orders:
        labels.append(entry['month'].strftime('%b'))
        revenue_data.append(float(entry['revenue'] or 0))
        order_data.append(entry['order_count'])

    return JsonResponse({
        'labels': labels,
        'revenue': revenue_data,
        'orders': order_data
    })



@user_passes_test(superuser_check, login_url='custom_admin:login')
@login_required(login_url='custom_admin:login')
def top_products_data(request):
    products = (OrderItem.objects
                .filter(order__status='DELIVERED')
                .values('product_name')
                .annotate(total_sold=Sum('quantity'))
                .order_by('-total_sold')[:10]
    )
    data = list(products)

    return JsonResponse(data, safe=False)


@user_passes_test(superuser_check, login_url='custom_admin:login')
@login_required(login_url='custom_admin:login')
def top_categories_data(request):
    categories = (OrderItem.objects
        .filter(order__status='DELIVERED')
        .values('product__category__name')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:10]
    )

    formatted = [{
            'category': item['product__category__name'],
            'total_sold': item['total_sold']
        }
        for item in categories
    ]

    return JsonResponse(formatted, safe=False)