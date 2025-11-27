# category_management/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Category
from .forms import CategoryForm, CategorySearchForm
import base64
from django.core.files.base import ContentFile
from django.utils import timezone

def superuser_check(user):
    return user.is_active and user.is_superuser

admin_required = [login_required(login_url='custom_admin:login'), user_passes_test(superuser_check, login_url='custom_admin:login')]



@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def category_list(request):

    form = CategorySearchForm(request.GET or None)  
    qs = Category.all_objects.filter(is_deleted=False).order_by('-created_at')

    if form.is_valid():
        q = form.cleaned_data.get('q')
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(description__icontains=q)

    page = request.GET.get('page', 1)
    per_page = 10
    paginator = Paginator(qs, per_page)
    try:
        categories = paginator.page(page)
    except PageNotAnInteger:
        categories = paginator.page(1)
    except EmptyPage:
        categories = paginator.page(paginator.num_pages)

    context = {
        'form': form,
        'categories': categories,
        'query': request.GET.get('q', '')
    }
    return render(request, 'category_management/category_list.html', context)



@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        cropped_data = request.POST.get('image')
        if cropped_data and cropped_data.startswith('data:image'):
            format, imgstr = cropped_data.split(';base64,')
            ext = format.split('/')[-1]
            file_name = f"cropped_{int(timezone.now().timestamp())}.{ext}"
            file_data = ContentFile(base64.b64decode(imgstr), name=file_name)
            request.FILES['image'] = file_data

        if form.is_valid():
            category = form.save()  
            messages.success(request, f'Category \"{category.name}\" created.')
            return redirect(reverse('category_management:category_list'))
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CategoryForm()

    return render(request, 'category_management/category_form.html', {'form': form, 'action': 'Create'})



@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def category_edit(request, pk):

    category = get_object_or_404(Category.all_objects, pk=pk)

    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)

        cropped_data = request.POST.get('image')
        if cropped_data and cropped_data.startswith('data:image'):
            format, imgstr = cropped_data.split(';base64,')
            ext = format.split('/')[-1]
            file_name = f"cropped_{int(timezone.now().timestamp())}.{ext}"
            file_data = ContentFile(base64.b64decode(imgstr), name=file_name)
            request.FILES['image'] = file_data

        if form.is_valid():
            form.save()  
            messages.success(request, f'Category \"{category.name}\" updated.')
            return redirect(reverse('category_management:category_list'))
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CategoryForm(instance=category)

    return render(request, 'category_management/category_form.html', {
        'form': form,
        'action': 'Edit',
        'category': category
    })



@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def category_delete_confirm(request, pk):

    category = get_object_or_404(Category.all_objects, pk=pk)
    if request.method == 'POST':
        category.is_deleted = True
        category.save()  
        messages.success(request, f'Category \"{category.name}\" deleted (soft).')
        return redirect(reverse('category_management:category_list'))
    return render(request, 'category_management/confirm_delete.html', {'category': category})



@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def category_toggle(request, category_id):

    category = get_object_or_404(Category.all_objects, id=category_id, is_deleted=False)
    category.is_listed = not category.is_listed  
    category.save() 
    state = "listed" if category.is_listed else "unlisted"
    messages.info(request, f'Category \"{category.name}\" is now {state}.')
    return redirect(reverse('custom_admin:category_management:category_list'))
