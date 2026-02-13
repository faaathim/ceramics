# category_management/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import Category
from .forms import CategoryForm, CategorySearchForm

import base64


# -------------------------------------------------------------------
# Permissions
# -------------------------------------------------------------------

def superuser_check(user):
    return user.is_active and user.is_superuser


# -------------------------------------------------------------------
# Category List
# -------------------------------------------------------------------

@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def category_list(request):
    form = CategorySearchForm(request.GET or None)

    qs = (
        Category.all_objects
        .filter(is_deleted=False)
        .prefetch_related('products')
        .order_by('-created_at')
    )

    if form.is_valid():
        q = form.cleaned_data.get('q')
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(description__icontains=q)
            )

    paginator = Paginator(qs, 10)
    page = request.GET.get('page', 1)

    try:
        categories = paginator.page(page)
    except PageNotAnInteger:
        categories = paginator.page(1)
    except EmptyPage:
        categories = paginator.page(paginator.num_pages)

    return render(request, 'category_management/category_list.html', {
        'form': form,
        'categories': categories,
        'query': request.GET.get('q', ''),
    })


# -------------------------------------------------------------------
# Category Create
# -------------------------------------------------------------------

@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def category_create(request):
    if request.method == 'POST':
        post_data = request.POST.copy()
        files_data = request.FILES.copy()

        cropped_data = post_data.get('image_cropped')
        if cropped_data and cropped_data.startswith('data:image'):
            format, imgstr = cropped_data.split(';base64,')
            ext = format.split('/')[-1]
            filename = f"category_{int(timezone.now().timestamp())}.{ext}"

            files_data['image'] = SimpleUploadedFile(
                name=filename,
                content=base64.b64decode(imgstr),
                content_type=f'image/{ext}'
            )

        # 🔑 Remove helper field so form never sees it
        post_data.pop('image_cropped', None)

        form = CategoryForm(post_data, files_data)

        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" created.')
            return redirect('custom_admin:category_management:category_list')

        messages.error(request, "Please correct the errors below.")
    else:
        form = CategoryForm()

    return render(request, 'category_management/category_form.html', {
        'form': form,
        'action': 'Create',
    })



# -------------------------------------------------------------------
# Category Edit
# -------------------------------------------------------------------
from django.core.files.uploadedfile import SimpleUploadedFile

@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def category_edit(request, pk):
    category = get_object_or_404(Category.all_objects, pk=pk)

    if request.method == 'POST':
        post_data = request.POST.copy()
        files_data = request.FILES.copy()

        cropped_data = post_data.get('image_cropped')

        if cropped_data and cropped_data.startswith('data:image'):
            format, imgstr = cropped_data.split(';base64,')
            ext = format.split('/')[-1]
            filename = f"category_{int(timezone.now().timestamp())}.{ext}"

            files_data['image'] = SimpleUploadedFile(
                name=filename,
                content=base64.b64decode(imgstr),
                content_type=f'image/{ext}'
            )
        else:
            # 🔑 CRITICAL: prevent Django from re-validating old file
            files_data.pop('image', None)

        # Remove helper field
        post_data.pop('image_cropped', None)

        form = CategoryForm(post_data, files_data, instance=category)

        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" updated.')
            return redirect('custom_admin:category_management:category_list')

        messages.error(request, "Please correct the errors below.")
    else:
        form = CategoryForm(instance=category)

    return render(request, 'category_management/category_form.html', {
        'form': form,
        'action': 'Edit',
        'category': category,
    })


# -------------------------------------------------------------------
# Category Delete (Soft Delete)
# -------------------------------------------------------------------

@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def category_delete_confirm(request, pk):
    category = get_object_or_404(Category.all_objects, pk=pk)

    if request.method == 'POST':
        category.soft_delete()
        messages.success(request, f'Category "{category.name}" deleted.')
        return redirect('custom_admin:category_management:category_list')

    return render(request, 'category_management/confirm_delete.html', {
        'category': category,
    })


# -------------------------------------------------------------------
# Category Toggle (List / Unlist)
# -------------------------------------------------------------------

@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def category_toggle(request, category_id):
    category = get_object_or_404(
        Category.all_objects,
        id=category_id,
        is_deleted=False
    )

    # Prevent listing empty categories
    if not category.is_listed and not category.products.exists():
        messages.warning(request, "Cannot list a category with no products.")
        return redirect('custom_admin:category_management:category_list')

    category.is_listed = not category.is_listed
    category.save(update_fields=['is_listed'])

    if not category.is_listed:
        category.products.update(is_listed=False)
    else:
        for product in category.products.all():
            if product.stock > 0:
                product.is_listed = True
                product.save(update_fields=['is_listed'])

    state = "listed" if category.is_listed else "unlisted"
    messages.info(request, f'Category "{category.name}" is now {state}.')

    return redirect('custom_admin:category_management:category_list')
