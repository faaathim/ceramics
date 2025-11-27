# product_management/views.py
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404, JsonResponse

from .models import Product, ProductImage, Variant, VariantImage, product_average_rating, get_related_products
from .forms import ProductForm, ProductSearchForm, VariantForm

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


# =============================================
# PRODUCT VIEWS
# =============================================

@admin_required
def product_list(request):
    """Backend search + pagination + newest-first sorting."""
    form = ProductSearchForm(request.GET or None)
    qs = Product.objects.all()

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
    Create product with improved validation messages:
    - Check if images are provided
    - Check if main image is provided
    - Enforce total images (main + gallery) between 3 and 7 inclusive
    """
    if request.method == 'POST':
        form = ProductForm(request.POST)
        main_file = request.FILES.get('main_image')
        gallery_files = request.FILES.getlist('images')

        # Step 1: Check if any images are provided
        if not main_file and not gallery_files:
            messages.error(request, "Please upload at least one image. Images are required to create a product.")
            return render(request, 'product_management/product_form.html', {
                'form': form, 'action': 'Create', 'product': None
            })

        # Step 2: Check if main image is provided
        if not main_file:
            messages.error(request, "Main image is mandatory. Please upload a main product image.")
            return render(request, 'product_management/product_form.html', {
                'form': form, 'action': 'Create', 'product': None
            })

        # Step 3: Count total images (main + gallery)
        total_images = 1 + len(gallery_files)  # main is always 1 if we reach here
        
        if total_images < 3:
            messages.error(request, f"Please provide at least 3 images in total. You have uploaded {total_images} image(s). You need {3 - total_images} more image(s).")
            return render(request, 'product_management/product_form.html', {
                'form': form, 'action': 'Create', 'product': None
            })
        
        if total_images > 7:
            messages.error(request, f"You can upload at most 7 images in total. You have uploaded {total_images} images. Please remove {total_images - 7} image(s).")
            return render(request, 'product_management/product_form.html', {
                'form': form, 'action': 'Create', 'product': None
            })

        # Step 4: Validate form
        if form.is_valid():
            product = form.save(commit=False)
            # Product starts with 0 stock and unlisted until variants are added
            product.stock = 0
            product.is_listed = False
            product.save()

            # Process main image
            main_filename = f'{product.id}_main.jpg'
            abs_main = os.path.join(settings.MEDIA_ROOT, 'products', 'main', main_filename)
            rel_main = os.path.join('products', 'main', main_filename)
            process_and_save_image(main_file, abs_main, size=(800, 800))
            product.main_image = rel_main
            product.save()

            # Process gallery images
            for idx, uploaded in enumerate(gallery_files):
                fname = f'{idx}_{uploaded.name}'
                rel_dir = os.path.join('products', str(product.id))
                abs_path = os.path.join(settings.MEDIA_ROOT, rel_dir, fname)
                rel_path = os.path.join(rel_dir, fname)
                process_and_save_image(uploaded, abs_path, size=(1024, 1024))
                ProductImage.objects.create(product=product, image=rel_path, order=idx)

            messages.success(request, f'Product "{product.name}" created successfully! Now add variants to list it for sale.')
            return redirect(reverse('custom_admin:product_management:variant_list', args=[product.id]))
        else:
            # Form validation errors
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm()

    return render(request, 'product_management/product_form.html', {
        'form': form, 'action': 'Create', 'product': None
    })


@admin_required
@transaction.atomic
def product_edit(request, pk):
    """Edit product with improved validation for images."""
    product = get_object_or_404(Product.all_objects, pk=pk)

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        main_file = request.FILES.get('main_image')
        gallery_files = request.FILES.getlist('images')
        
        # Check if user wants to remove images
        remove_main = request.POST.get('remove_main_image') == 'true'
        remove_gallery = request.POST.get('remove_gallery_images') == 'true'

        # ===== IMAGE COUNTING LOGIC =====

        # Determine if main image will exist
        if main_file:
            will_have_main = True
        elif product.main_image and not remove_main:
            will_have_main = True
        else:
            will_have_main = False

        # Determine gallery count
        if remove_gallery:
            existing_gallery = 0
        else:
            existing_gallery = product.images.count()

        new_gallery = len(gallery_files)

        # If new gallery files are uploaded → they replace existing gallery
        if new_gallery > 0:
            gallery_after = new_gallery
        else:
            gallery_after = existing_gallery

        total_after = (1 if will_have_main else 0) + gallery_after

        # ===== VALIDATION =====
        if total_after < 3:
            messages.error(request, f"Total images must be at least 3. After your changes, you will have {total_after} image(s). Please add {3 - total_after} more image(s).")
        elif total_after > 7:
            messages.error(request, f"Total images cannot exceed 7. After your changes, you will have {total_after} image(s). Please remove {total_after - 7} image(s).")
        else:
            if form.is_valid():
                product = form.save(commit=False)
                
                # Handle main image removal
                if remove_main and product.main_image:
                    try:
                        if os.path.isfile(product.main_image.path):
                            os.remove(product.main_image.path)
                    except Exception:
                        pass
                    product.main_image = None

                # Handle main image replacement
                if main_file:
                    try:
                        if product.main_image and os.path.isfile(product.main_image.path):
                            os.remove(product.main_image.path)
                    except Exception:
                        pass
                    main_filename = f'{product.id}_main.jpg'
                    abs_main = os.path.join(settings.MEDIA_ROOT, 'products', 'main', main_filename)
                    rel_main = os.path.join('products', 'main', main_filename)
                    process_and_save_image(main_file, abs_main, size=(800, 800))
                    product.main_image = rel_main

                # Handle gallery removal
                if remove_gallery:
                    for old in product.images.all():
                        try:
                            if old.image and os.path.isfile(old.image.path):
                                os.remove(old.image.path)
                        except Exception:
                            pass
                    product.images.all().delete()

                # Handle gallery replacement
                if gallery_files:
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
                        process_and_save_image(uploaded, abs_path, size=(1024, 1024))
                        ProductImage.objects.create(product=product, image=rel_path, order=idx)

                # If no main image but gallery exists, set first as main
                if not product.main_image and product.images.exists():
                    product.main_image = product.images.first().image.name

                product.save()
                messages.success(request, f'Product "{product.name}" updated successfully!')
                return redirect(reverse('custom_admin:product_management:product_list'))
            else:
                messages.error(request, "Please correct the errors below.")

    else:
        form = ProductForm(instance=product)

    return render(request, 'product_management/product_edit.html', {
        'form': form, 'action': 'Edit', 'product': product
    })



@admin_required
def product_delete(request, pk):
    """Soft delete product via POST"""
    product = get_object_or_404(Product.all_objects, pk=pk)
    if request.method == 'POST':
        product.is_deleted = True
        product.save()
        messages.success(request, f'Product "{product.name}" deleted successfully.')
        return redirect(reverse('custom_admin:product_management:product_list'))
    return redirect(reverse('custom_admin:product_management:product_list'))


@admin_required
def product_toggle_listing(request, pk):
    """Toggle product listing status (only if it has variants)"""
    product = get_object_or_404(Product.all_objects, pk=pk)
    
    if request.method == 'POST':
        if product.can_be_listed():
            product.is_listed = not product.is_listed
            product.save()
            status = "listed" if product.is_listed else "unlisted"
            messages.success(request, f'Product "{product.name}" {status} successfully.')
        else:
            messages.error(request, f'Cannot list product "{product.name}" - add variants first.')
    
    return redirect(reverse('custom_admin:product_management:product_list'))




# =============================================
# VARIANT VIEWS
# =============================================

@admin_required
def variant_list(request, product_pk):
    product = get_object_or_404(Product.all_objects, pk=product_pk)
    if product.is_deleted:
        messages.error(request, "Product not available.")
        return redirect(reverse('custom_admin:product_management:product_list'))

    q = request.GET.get('q', '').strip()
    qs = product.variants.filter(is_deleted=False)
    if q:
        qs = qs.filter(color__icontains=q)

    page = request.GET.get('page', 1)
    paginator = Paginator(qs, 10)
    try:
        variants = paginator.page(page)
    except PageNotAnInteger:
        variants = paginator.page(1)
    except EmptyPage:
        variants = paginator.page(paginator.num_pages)

    return render(request, 'product_management/variant_list.html', {
        'product': product, 'variants': variants, 'query': q
    })


@admin_required
@transaction.atomic
def variant_create(request, product_pk):
    product = get_object_or_404(Product.all_objects, pk=product_pk)
    if request.method == 'POST':
        form = VariantForm(request.POST, request.FILES)
        main_file = request.FILES.get('main_image')
        gallery_files = request.FILES.getlist('images')

        total_images = (1 if main_file else 0) + len(gallery_files)
        if total_images < 3:
            messages.error(request, "Please provide at least 3 images in total (including main image).")
        elif total_images > 7:
            messages.error(request, "You can upload at most 7 images in total (including main image).")
        else:
            if form.is_valid():
                variant = form.save(commit=False)
                variant.product = product
                
                # If stock is 0, force unlist
                if variant.stock == 0:
                    variant.is_listed = False
                
                variant.save()

                # process main image
                if main_file:
                    main_filename = f'{variant.id}_main.jpg'
                    abs_main = os.path.join(settings.MEDIA_ROOT, 'products', str(product.id), 'variants', f'{variant.id}', main_filename)
                    rel_main = os.path.join('products', str(product.id), 'variants', f'{variant.id}', main_filename)
                    process_and_save_image(main_file, abs_main, size=(800,800))
                    variant.main_image = rel_main
                    variant.save()

                # gallery images
                for idx, uploaded in enumerate(gallery_files):
                    fname = f'{idx}_{uploaded.name}'
                    rel_dir = os.path.join('products', str(product.id), 'variants', str(variant.id))
                    abs_path = os.path.join(settings.MEDIA_ROOT, rel_dir, fname)
                    rel_path = os.path.join(rel_dir, fname)
                    process_and_save_image(uploaded, abs_path, size=(1024,1024))
                    VariantImage.objects.create(variant=variant, image=rel_path, order=idx)

                # if main_image not provided but gallery present -> set first as main
                if not variant.main_image and variant.images.exists():
                    first = variant.images.first()
                    variant.main_image = first.image.name
                    variant.save()

                # Update product stock
                product.update_stock()

                messages.success(request, f'Variant created successfully for "{product.name}".')
                return redirect(reverse('custom_admin:product_management:variant_list', args=[product.id]))
    else:
        form = VariantForm()

    return render(request, 'product_management/variant_form.html', {
        'form': form, 'action': 'Create', 'product': product, 'variant': None
    })


@admin_required
@transaction.atomic
def variant_edit(request, product_pk, pk):
    product = get_object_or_404(Product.all_objects, pk=product_pk)
    variant = get_object_or_404(Variant, pk=pk)

    if variant.product_id != product.id:
        raise Http404

    if request.method == 'POST':
        form = VariantForm(request.POST, request.FILES, instance=variant)
        main_file = request.FILES.get('main_image')
        gallery_files = request.FILES.getlist('images')
        
        # Check removals
        remove_main = request.POST.get('remove_main_image') == 'true'
        remove_gallery = request.POST.get('remove_gallery_images') == 'true'

        # ===== FIXED IMAGE COUNTING LOGIC =====

        # Determine if main image will exist
        if main_file:
            will_have_main = True
        elif variant.main_image and not remove_main:
            will_have_main = True
        else:
            will_have_main = False

        # Determine gallery count
        if remove_gallery:
            existing_gallery = 0
        else:
            existing_gallery = variant.images.count()

        new_gallery = len(gallery_files)

        # New gallery always replaces old
        if new_gallery > 0:
            gallery_after = new_gallery
        else:
            gallery_after = existing_gallery

        total_after = (1 if will_have_main else 0) + gallery_after

        # ===== VALIDATION =====
        if total_after < 3:
            messages.error(request, "Total images (main + gallery) must be at least 3.")
        elif total_after > 7:
            messages.error(request, "Total images (main + gallery) cannot exceed 7.")
        else:
            if form.is_valid():
                variant = form.save(commit=False)
                
                # If stock is 0, force unlist
                if variant.stock == 0:
                    variant.is_listed = False

                # Handle main image removal
                if remove_main and variant.main_image:
                    try:
                        path = os.path.join(settings.MEDIA_ROOT, variant.main_image.name)
                        if os.path.isfile(path):
                            os.remove(path)
                    except Exception:
                        pass
                    variant.main_image = None

                # replace main image
                if main_file:
                    try:
                        path = os.path.join(settings.MEDIA_ROOT, variant.main_image.name)
                        if variant.main_image and os.path.isfile(path):
                            os.remove(path)
                    except Exception:
                        pass
                    main_filename = f'{variant.id}_main.jpg'
                    abs_main = os.path.join(settings.MEDIA_ROOT, 'products', str(product.id), 'variants', str(variant.id), main_filename)
                    rel_main = os.path.join('products', str(product.id), 'variants', str(variant.id), main_filename)
                    process_and_save_image(main_file, abs_main, size=(800,800))
                    variant.main_image = rel_main

                # Handle gallery removal
                if remove_gallery:
                    for old in variant.images.all():
                        try:
                            path = os.path.join(settings.MEDIA_ROOT, old.image.name)
                            if os.path.isfile(path):
                                os.remove(path)
                        except Exception:
                            pass
                    variant.images.all().delete()

                # replace gallery
                if gallery_files:
                    for old in variant.images.all():
                        try:
                            path = os.path.join(settings.MEDIA_ROOT, old.image.name)
                            if os.path.isfile(path):
                                os.remove(path)
                        except Exception:
                            pass
                    variant.images.all().delete()
                    
                    for idx, uploaded in enumerate(gallery_files):
                        fname = f'{idx}_{uploaded.name}'
                        rel_dir = os.path.join('products', str(product.id), 'variants', str(variant.id))
                        abs_path = os.path.join(settings.MEDIA_ROOT, rel_dir, fname)
                        rel_path = os.path.join(rel_dir, fname)
                        process_and_save_image(uploaded, abs_path, size=(1024,1024))
                        VariantImage.objects.create(variant=variant, image=rel_path, order=idx)

                if not variant.main_image and variant.images.exists():
                    variant.main_image = variant.images.first().image.name

                variant.save()
                product.update_stock()

                messages.success(request, 'Variant updated successfully.')
                return redirect(reverse('custom_admin:product_management:variant_list', args=[product.id]))
    else:
        form = VariantForm(instance=variant)

    return render(request, 'product_management/variant_edit.html', {
        'form': form, 'action': 'Edit', 'product': product, 'variant': variant
    })



@admin_required
def variant_delete_confirm(request, product_pk, pk):
    product = get_object_or_404(Product.all_objects, pk=product_pk)
    variant = get_object_or_404(Variant, pk=pk)
    if variant.product_id != product.id:
        raise Http404

    if request.method == 'POST':
        variant.is_deleted = True
        variant.save()
        product.update_stock()
        messages.success(request, 'Variant deleted successfully.')
        return redirect(reverse('custom_admin:product_management:variant_list', args=[product.id]))

    return render(request, 'product_management/confirm_delete_variant.html', {'product': product, 'variant': variant})


@admin_required
def variant_toggle_listing(request, product_pk, pk):
    """Toggle variant listing status (only if stock > 0)"""
    product = get_object_or_404(Product.all_objects, pk=product_pk)
    variant = get_object_or_404(Variant, pk=pk)
    
    if variant.product_id != product.id:
        raise Http404
    
    if request.method == 'POST':
        if variant.can_be_listed():
            variant.is_listed = not variant.is_listed
            variant.save()
            status = "listed" if variant.is_listed else "unlisted"
            messages.success(request, f'Variant {status} successfully.')
        else:
            messages.error(request, 'Cannot list variant with 0 stock. Please add stock first.')
    
    return redirect(reverse('custom_admin:product_management:variant_list', args=[product.id]))

def product_detail(request, pk):
    """
    Simple product page that loads a product and shows variants.
    Supports ?variant=<id> to switch between colors.
    """
    product = get_object_or_404(Product, pk=pk, is_deleted=False)

    # Get all listed variants
    variants = product.variants.filter(is_deleted=False, is_listed=True)

    if not variants.exists():
        raise Http404("No variants available for this product.")

    # Check URL for selected variant
    variant_id = request.GET.get("variant")

    if variant_id:
        try:
            selected_variant = variants.get(id=variant_id)
        except Variant.DoesNotExist:
            selected_variant = variants.first()
    else:
        selected_variant = variants.first()

    return render(request, "product_management/product_variant_detail.html", {
        "product": product,
        "variant": selected_variant,
        "variants": variants,
    })

def variant_json(request, variant_id):
    """
    Returns JSON data for a variant (used when switching colors).
    """
    variant = get_object_or_404(Variant, id=variant_id, is_deleted=False, is_listed=True)

    data = {
        "id": variant.id,
        "color": variant.color,
        "stock": variant.stock,
        "image": variant.main_image.url if variant.main_image else "",
    }

    return JsonResponse(data)

