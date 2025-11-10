# product_management/views.py
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import Product, ProductImage, product_average_rating, get_related_products

from .forms import ProductForm, ProductSearchForm

from PIL import Image

# permission decorator: allow only active superusers
def superuser_check(user):
    return user.is_active and user.is_superuser

def admin_required(view_func):
    return login_required(user_passes_test(superuser_check, login_url='custom_admin:login')(view_func), login_url='custom_admin:login')

# helper: process and save an uploaded image to an absolute path
def process_and_save_image(uploaded_file, abs_save_path, size=(1024,1024)):
    """
    Crop center square and resize to `size`, save as JPEG with quality 85.
    abs_save_path: absolute filesystem path (including filename).
    """
    img = Image.open(uploaded_file)
    img = img.convert('RGB')
    w, h = img.size
    edge = min(w, h)
    left = (w - edge) / 2
    top = (h - edge) / 2
    img = img.crop((left, top, left + edge, top + edge))
    img = img.resize(size, Image.LANCZOS)
    os.makedirs(os.path.dirname(abs_save_path), exist_ok=True)
    img.save(abs_save_path, 'JPEG', quality=85)

@admin_required
def product_list(request):
    """Backend search + pagination + newest-first sorting."""
    form = ProductSearchForm(request.GET or None)
    qs = Product.objects.all()  # manager excludes deleted

    if form.is_valid():
        q = form.cleaned_data.get('q')
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(description__icontains=q)

    page = request.GET.get('page', 1)
    per_page = 10
    paginator = Paginator(qs, per_page)
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    return render(request, 'product_management/product_list.html', {
        'form': form, 'products': products, 'query': request.GET.get('q', '')
    })


@admin_required
@transaction.atomic
def product_create(request):
    """
    Create product:
    - main_image_file: single uploaded file from 'main_image'
    - gallery_files: list from 'images' (multi-file input)
    - Enforce total images (main + gallery) between 3 and 7 inclusive.
    - Process images: main -> 800x800; gallery -> 1024x1024.
    """
    if request.method == 'POST':
        form = ProductForm(request.POST)
        main_file = request.FILES.get('main_image')
        gallery_files = request.FILES.getlist('images')  # can be empty list

        # count total images (main + gallery)
        total_images = (1 if main_file else 0) + len(gallery_files)
        if total_images < 3:
            messages.error(request, "Please provide at least 3 images in total (including main image).")
        elif total_images > 7:
            messages.error(request, "You can upload at most 7 images in total (including main image).")
        else:
            if form.is_valid():
                product = form.save(commit=False)
                product.save()  # need id to build file paths

                # process main image if provided
                if main_file:
                    main_filename = f'{product.id}_main.jpg'
                    abs_main = os.path.join(settings.MEDIA_ROOT, 'products', 'main', main_filename)
                    rel_main = os.path.join('products', 'main', main_filename)
                    process_and_save_image(main_file, abs_main, size=(800,800))
                    product.main_image = rel_main
                    product.save()

                # process gallery images (order them after main if both exist)
                for idx, uploaded in enumerate(gallery_files):
                    fname = f'{idx}_{uploaded.name}'
                    rel_dir = os.path.join('products', str(product.id))
                    abs_path = os.path.join(settings.MEDIA_ROOT, rel_dir, fname)
                    rel_path = os.path.join(rel_dir, fname)
                    process_and_save_image(uploaded, abs_path, size=(1024,1024))
                    ProductImage.objects.create(product=product, image=rel_path, order=idx)

                # If main image not provided, set first gallery image as main automatically
                if not product.main_image and product.images.exists():
                    first = product.images.first()
                    # copy reference to main_image field
                    product.main_image = first.image.name
                    product.save()

                messages.success(request, f'Product "{product.name}" created.')
                return redirect(reverse('custom_admin:product_management:product_list'))
    else:
        form = ProductForm()

    return render(request, 'product_management/product_form.html', {
        'form': form, 'action': 'Create', 'product': None
    })


@admin_required
@transaction.atomic
def product_edit(request, pk):
    """
    Edit product.
    If new images uploaded in gallery, replace old ones.
    If main image uploaded, replace main image.
    Maintain total image count constraints when new images provided.
    """
    product = get_object_or_404(Product.all_objects, pk=pk)

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        main_file = request.FILES.get('main_image')
        gallery_files = request.FILES.getlist('images')

        # compute total images after applying changes:
        # if gallery_files provided then they will replace old gallery
        current_gallery_count = 0 if gallery_files else product.images.count()
        total_after = (1 if main_file or product.main_image else 0) + current_gallery_count + (len(gallery_files) if gallery_files else 0)
        # but above double counts; simpler: if main_file provided -> will exist; if gallery_files provided -> use len(gallery_files), else existing count
        main_exists = True if (main_file or product.main_image) else False
        gallery_count_after = len(gallery_files) if gallery_files else product.images.count()
        total_after = (1 if main_exists else 0) + gallery_count_after

        if total_after < 3:
            messages.error(request, "Total images (main + gallery) must be at least 3.")
            return render(request, 'product_management/product_form.html', {'form': form, 'action': 'Edit', 'product': product})
        if total_after > 7:
            messages.error(request, "Total images (main + gallery) cannot exceed 7.")
            return render(request, 'product_management/product_form.html', {'form': form, 'action': 'Edit', 'product': product})

        if form.is_valid():
            product = form.save(commit=False)
            product.save()

            # handle main image replacement
            if main_file:
                # delete old main file
                try:
                    if product.main_image and os.path.isfile(product.main_image.path):
                        os.remove(product.main_image.path)
                except Exception:
                    pass
                main_filename = f'{product.id}_main.jpg'
                abs_main = os.path.join(settings.MEDIA_ROOT, 'products', 'main', main_filename)
                rel_main = os.path.join('products', 'main', main_filename)
                process_and_save_image(main_file, abs_main, size=(800,800))
                product.main_image = rel_main
                product.save()

            # handle gallery replacement if new gallery files uploaded
            if gallery_files:
                # delete old gallery files from disk & DB
                for old in product.images.all():
                    try:
                        if old.image and os.path.isfile(old.image.path):
                            os.remove(old.image.path)
                    except Exception:
                        pass
                product.images.all().delete()
                for idx, uploaded in enumerate(gallery_files):
                    fname = f'{idx}_{uploaded.name}'
                    rel_dir = os.path.join('products', str(product.id))
                    abs_path = os.path.join(settings.MEDIA_ROOT, rel_dir, fname)
                    rel_path = os.path.join(rel_dir, fname)
                    process_and_save_image(uploaded, abs_path, size=(1024,1024))
                    ProductImage.objects.create(product=product, image=rel_path, order=idx)

                # if no explicit main_file provided, set first gallery as main
                if not main_file and product.images.exists():
                    product.main_image = product.images.first().image.name
                    product.save()

            messages.success(request, f'Product "{product.name}" updated.')
            return redirect(reverse('custom_admin:product_management:product_list'))

    else:
        form = ProductForm(instance=product)

    return render(request, 'product_management/product_form.html', {
        'form': form, 'action': 'Edit', 'product': product
    })


@admin_required
def product_delete_confirm(request, pk):
    """Soft delete product: set is_deleted=True"""
    product = get_object_or_404(Product.all_objects, pk=pk)
    if request.method == 'POST':
        product.is_deleted = True
        product.save()
        messages.success(request, f'Product "{product.name}" deleted (soft).')
        return redirect(reverse('custom_admin:product_management:product_list'))
    return render(request, 'product_management/confirm_delete.html', {'product': product})


def product_detail(request, pk):
    """
    Show product detail.
    - If product is not available (deleted or not listed), redirect to shop with message.
    - Provides images, ratings, stock info, breadcrumbs, related products.
    """
    product = get_object_or_404(Product.all_objects, pk=pk)  # use all_objects to check flags

    # If product is soft-deleted or unlisted, redirect to shop
    if product.is_deleted or not product.is_listed:
        messages.error(request, "Product is not available.")
        return redirect('user_side:shop')

    # aggregated rating and reviews
    avg_rating, review_count = product_average_rating(product)

    # related products
    related = get_related_products(product, limit=6)

    # prepare breadcrumbs (Home > Category > Product)
    breadcrumbs = [
        ('Home', reverse('user_side:home')),
    ]
    if getattr(product, 'category', None):
        breadcrumbs.append((product.category.name, reverse('user_side:shop') + f'?category={product.category.id}'))
    breadcrumbs.append((product.name, None))

    context = {
        'product': product,
        'avg_rating': avg_rating,
        'review_count': review_count,
        'related_products': related,
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'product_management/product_detail.html', context)
