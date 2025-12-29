from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import AdminLoginForm


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
    return render(request, 'custom_admin/dashboard.html', {
        'admin_name': request.user.get_full_name() or request.user.username,
    })
