from django.shortcuts import render, redirect, get_object_or_404
from category.models import Category
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from admin_panel.views import superuser_required
from category.forms import CategoryForm
from django.views.decorators.cache import never_cache

# Create your views here.

# category list

@superuser_required
@never_cache
def category_list(request):
    query = request.GET.get('q', '')
    page_number = request.GET.get('page', 1)
    sort_by = request.GET.get('sort', '-created_at')

    categories = Category.objects.filter(is_deleted=False)

    if query:
        categories = categories.filter(Q(name__icontains=query) | Q(description__icontains=query))

    valid_sort_fields = ['name', '-name', 'created_at', '-created_at', 'is_listed', '-is_listed']
    if sort_by not in valid_sort_fields:
        sort_by = '-created_at'
    
    categories = categories.order_by(sort_by)

    paginator = Paginator(categories, 10)
    page_obj = paginator.get_page(page_number)

    return render(request, 'category/category_list.html', {
        'categories': page_obj,
        'query': query,
        'sort_by': sort_by,
    })


# add category

@superuser_required
@never_cache
def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Category added successfully.")
            return redirect('category_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CategoryForm()

    return render(request, 'category/category_form.html', {'form': form, 'title': 'Add Category'})


# edit category

@superuser_required
@never_cache
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully.")
            return redirect('category_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CategoryForm(instance=category)

    return render(request, 'category/category_form.html', {'form': form, 'title': 'Edit Category'})


# delete category

@superuser_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if category.is_deleted:
        return redirect('category_list')

    linked_products_count = category.products.filter(is_deleted=False).count() if hasattr(category, 'products') else 0

    if request.method == 'POST':
        # Soft delete
        category.is_deleted = True
        category.save()
        messages.success(request, "Category deleted.")
        return redirect('category_list')

    return render(request, 'category/delete_confirmation.html', {
        'category': category,
        'linked_products_count': linked_products_count,
    })


