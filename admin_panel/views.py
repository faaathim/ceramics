from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from user_auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import never_cache

# Create your views here.

# protect admin panel with superuser access

def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_superuser)(view_func)


# admin dashboard

@superuser_required
@never_cache
def dashboard(request):
    return render(request, 'admin_panel/dashboard.html')


# admin login 

@never_cache
def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user and user.is_superuser:
            login(request, user)
            return redirect('admin_dashboard')
        else: 
            messages.error(request, 'Invalid credentials or not authorized.')
    return render(request, 'admin_panel/admin_login.html')


# admin logout

@superuser_required
def admin_logout(request):
    logout(request)
    return redirect('admin_login')

# user list

@superuser_required
@never_cache
def user_list(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    page_number = request.GET.get('page', 1)

    users = User.objects.all()

    # Apply search
    if query:
        users = users.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        )

    # Apply status filter
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)

    # Always newest first
    users = users.order_by('-date_joined')

    paginator = Paginator(users, 10)
    page_obj = paginator.get_page(page_number)

    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    return render(request, 'admin_panel/user_list.html', {
        'users': page_obj,
        'query': query,
        'status_filter': status_filter,
        'months': months
    })




# block user

@superuser_required
def block_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user == request.user:
        messages.error(request, "You cannot block the currently logged-in user.")
        return redirect('user_list')
    user.is_blocked = True
    user.save()
    messages.success(request, f"{user.username} has been blocked.")
    return redirect('user_list')


# unblock user

@superuser_required
def unblock_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_blocked = False
    user.save()
    messages.success(request, f"{user.username} has been unblocked.")
    return redirect('user_list')


