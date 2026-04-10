# user_management/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import user_passes_test, login_required
from django.urls import reverse
from .forms import UserSearchForm


def superuser_check(user):
    return user.is_active and user.is_superuser


admin_required = user_passes_test(superuser_check, login_url='custom_admin:login')


@admin_required
@login_required(login_url='custom_admin:login')
def user_list(request):
    form = UserSearchForm(request.GET or None)
    qs = User.objects.all().order_by('-date_joined')

    if form.is_valid():
        q = form.cleaned_data.get('q')
        if q:
            qs = qs.filter(
                username__icontains=q
            ) | qs.filter(email__icontains=q)

    page = request.GET.get('page', 1)
    per_page = 10

    paginator = Paginator(qs, per_page)
    try:
        users_page = paginator.page(page)
    except PageNotAnInteger:
        users_page = paginator.page(1)
    except EmptyPage:
        users_page = paginator.page(paginator.num_pages)

    context = {
        'form': form,
        'users_page': users_page,
        'query': request.GET.get('q', ''),
    }
    return render(request, 'user_management/user_list.html', context)


@admin_required
@login_required(login_url='custom_admin:login')
def confirm_toggle(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)

    if target_user == request.user:
        messages.error(request, "You cannot block/unblock your own account.")
        return redirect(reverse('custom_admin:user_management:user_list'))

    action = 'Unblock' if target_user.is_active == False else 'Block'

    if request.method == 'POST':
        target_user.is_active = not target_user.is_active
        target_user.save()
        messages.success(request, f"{target_user.username} has been {action.lower()}ed.")
        return redirect(reverse('custom_admin:user_management:user_list'))

    context = {
        'target_user': target_user,
        'action': action,
    }
    return render(request, 'user_management/confirm_toggle.html', context)