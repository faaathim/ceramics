# category_management/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.utils import timezone
from .models import Category
from .forms import CategoryForm, CategorySearchForm



def superuser_check(user):
    return user.is_active and user.is_superuser


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


@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def category_create(request):

    if request.method == 'POST':

        form = CategoryForm(request.POST)

        if form.is_valid():

            category = form.save()

            messages.success(
                request,
                f'Category "{category.name}" created successfully.'
            )

            return redirect(
                'custom_admin:category_management:category_list'
            )

        messages.error(
            request,
            "Please correct the errors below."
        )

    else:
        form = CategoryForm()

    return render(request, 'category_management/category_form.html', {
        'form': form,
        'action': 'Create',
    })


@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def category_edit(request, pk):

    category = get_object_or_404(
        Category.all_objects,
        pk=pk
    )

    if request.method == 'POST':

        form = CategoryForm(
            request.POST,
            instance=category
        )

        if form.is_valid():

            updated_category = form.save()

            messages.success(
                request,
                f'Category "{updated_category.name}" updated successfully.'
            )

            return redirect(
                'custom_admin:category_management:category_list'
            )

        messages.error(
            request,
            "Please correct the errors below."
        )

    else:
        form = CategoryForm(instance=category)

    return render(request, 'category_management/category_form.html', {
        'form': form,
        'action': 'Edit',
        'category': category,
    })


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


@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def category_toggle(request, category_id):
    category = get_object_or_404(
        Category.all_objects,
        id=category_id,
        is_deleted=False
    )

    if not category.is_listed and not category.products.filter(is_deleted=False).exists():
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