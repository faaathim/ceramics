# product_management/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404, JsonResponse

from .models import Product, ProductImage, Variant, VariantImage, product_average_rating, get_related_products
from .forms import ProductForm, ProductSearchForm, VariantForm

def superuser_check(user):
    return user.is_active and user.is_superuser

def admin_required(view_func):
    return login_required(user_passes_test(superuser_check, login_url='custom_admin:login')(view_func), login_url='custom_admin:login')


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
    Create product with improved validation and error messages
    """
    if request.method == 'POST':
        form = ProductForm(request.POST)
        main_file = request.FILES.get('main_image')
        gallery_files = request.FILES.getlist('images')

        # Step 1: Check if any images are provided
        if not main_file and not gallery_files:
            form.add_error(None, "Please upload at least one image. Images are required to create a product.")
            return render(request, 'product_management/product_form.html', {
                'form': form, 'action': 'Create', 'product': None
            })

        # Step 2: Check if main image is provided
        if not main_file:
            form.add_error(None, "Main image is mandatory. Please upload a main product image.")
            return render(request, 'product_management/product_form.html', {
                'form': form, 'action': 'Create', 'product': None
            })

        # Step 3: Count total images (main + gallery)
        total_images = 1 + len(gallery_files)
        
        if total_images < 3:
            form.add_error(None, f"Please provide at least 3 images in total. You have uploaded {total_images} image(s). You need {3 - total_images} more image(s).")
            return render(request, 'product_management/product_form.html', {
                'form': form, 'action': 'Create', 'product': None
            })
        
        if total_images > 7:
            form.add_error(None, f"You can upload at most 7 images in total. You have uploaded {total_images} images. Please remove {total_images - 7} image(s).")
            return render(request, 'product_management/product_form.html', {
                'form': form, 'action': 'Create', 'product': None
            })

        # Step 4: Validate form
        if form.is_valid():
            try:
                product = form.save(commit=False)
                # Product starts with 0 stock and unlisted until variants are added
                product.stock = 0
                product.is_listed = False
                product.save()

                # Process main image
                product.main_image = main_file
                product.save(update_fields=['main_image'])

                # Process gallery images
                for idx, uploaded in enumerate(gallery_files):
                    ProductImage.objects.create(
                        product=product,
                        image=uploaded,
                        order=idx
    )

                messages.success(request, f'Product "{product.name}" created successfully! Now add variants to list it for sale.')
                return redirect(reverse('custom_admin:product_management:variant_list', args=[product.id]))
            
            except Exception as e:
                # Rollback will happen automatically due to @transaction.atomic
                messages.error(request, f"Error creating product: {str(e)}")
                return render(request, 'product_management/product_form.html', {
                    'form': form, 'action': 'Create', 'product': None
                })
        else:
            # Form validation errors - these will be displayed in the template
            pass

    else:
        form = ProductForm()

    return render(request, 'product_management/product_form.html', {
        'form': form, 'action': 'Create', 'product': None
    })


@admin_required
@transaction.atomic
def product_edit(request, pk):
    product = get_object_or_404(Product.all_objects, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)

        main_file = request.FILES.get("main_image")
        gallery_files = request.FILES.getlist("images")

        # Check if remove checkboxes are selected
        remove_main = "remove_main_image" in request.POST
        remove_gallery = "remove_gallery_images" in request.POST

        # -----------------------------
        # STEP 1: COUNT IMAGES AFTER EDIT
        # -----------------------------

        # MAIN IMAGE CHECK
        if main_file:
            will_have_main = True
        elif remove_main:
            will_have_main = False
        else:
            will_have_main = bool(product.main_image)

        # GALLERY IMAGE CHECK
        existing_gallery_count = product.images.count()
        new_gallery_count = len(gallery_files)

        if new_gallery_count > 0:
            # New uploads replace old gallery
            gallery_after = new_gallery_count
        elif remove_gallery:
            gallery_after = 0
        else:
            gallery_after = existing_gallery_count

        total_images_after = (1 if will_have_main else 0) + gallery_after

        # -----------------------------
        # STEP 2: VALIDATE IMAGE LIMIT
        # -----------------------------

        if total_images_after < 3:
            messages.error(
                request,
                f"Minimum 3 images required. After update you will have {total_images_after}. "
                f"Please add {3 - total_images_after} more image(s)."
            )
            return render(request, "product_management/product_edit.html", {
                "form": form,
                "product": product
            })

        if total_images_after > 7:
            messages.error(
                request,
                f"Maximum 7 images allowed. After update you will have {total_images_after}. "
                f"Please remove {total_images_after - 7} image(s)."
            )
            return render(request, "product_management/product_edit.html", {
                "form": form,
                "product": product
            })

        # -----------------------------
        # STEP 3: SAVE PRODUCT
        # -----------------------------

        if form.is_valid():
            product = form.save(commit=False)

            # ===== MAIN IMAGE HANDLING =====

            if remove_main and product.main_image:
                try:
                    if os.path.isfile(product.main_image.path):
                        os.remove(product.main_image.path)
                except Exception:
                    pass
                product.main_image = None

            if main_file:
                # Remove old main image
                try:
                    if product.main_image and os.path.isfile(product.main_image.path):
                        os.remove(product.main_image.path)
                except Exception:
                    pass

                product.main_image = main_file

            # ===== GALLERY HANDLING =====

            if remove_gallery:
                for img in product.images.all():
                    try:
                        if img.image and os.path.isfile(img.image.path):
                            os.remove(img.image.path)
                    except Exception:
                        pass
                product.images.all().delete()

            if gallery_files:
                # Remove old gallery images
                for img in product.images.all():
                    try:
                        if img.image and os.path.isfile(img.image.path):
                            os.remove(img.image.path)
                    except Exception:
                        pass
                product.images.all().delete()

                # Add new gallery images
                for index, uploaded in enumerate(gallery_files):
                    ProductImage.objects.create(
                        product=product,
                        image=uploaded,
                        order=index
                    )

            # If no main image but gallery exists → set first gallery image as main
            if not product.main_image and product.images.exists():
                product.main_image = product.images.first().image

            product.save()

            messages.success(request, "Product updated successfully!")
            return redirect("custom_admin:product_management:product_list")

        else:
            messages.error(request, "Please correct the errors below.")

    else:
        form = ProductForm(instance=product)

    return render(request, "product_management/product_edit.html", {
        "form": form,
        "product": product
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
            messages.error(request, "Please upload at least 3 images.")
        elif total_images > 7:
            messages.error(request, "You can upload at most 7 images.")
        elif form.is_valid():
            variant = form.save(commit=False)
            variant.product = product

            if variant.stock == 0:
                variant.is_listed = False

            variant.save()

            # MAIN IMAGE
            if main_file:
                variant.main_image = main_file
                variant.save(update_fields=["main_image"])

            # GALLERY IMAGES
            for idx, img in enumerate(gallery_files):
                VariantImage.objects.create(
                    variant=variant,
                    image=img,
                    order=idx
                )

            # AUTO MAIN IMAGE
            if not variant.main_image and variant.images.exists():
                variant.main_image = variant.images.first().image
                variant.save(update_fields=["main_image"])

            product.update_stock()
            messages.success(request, "Variant created successfully.")
            return redirect(
                reverse('custom_admin:product_management:variant_list', args=[product.id])
            )
    else:
        form = VariantForm()

    return render(request, 'product_management/variant_form.html', {
        'form': form,
        'action': 'Create',
        'product': product
    })


@admin_required
@transaction.atomic
def variant_edit(request, product_pk, pk):
    product = get_object_or_404(Product.all_objects, pk=product_pk)
    variant = get_object_or_404(Variant, pk=pk, product=product)

    if request.method == "POST":
        form = VariantForm(request.POST, request.FILES, instance=variant)

        main_file = request.FILES.get("main_image")
        gallery_files = request.FILES.getlist("images")

        remove_main = request.POST.get("remove_main_image") == "1"
        remove_gallery = request.POST.get("remove_gallery_images") == "1"

        # -------------------------
        # STEP 1: Validate form
        # -------------------------
        if not form.is_valid():
            messages.error(request, "Please correct the errors below.")
            return render(
                request,
                "product_management/variant_form.html",
                {"form": form, "action": "Edit", "product": product, "variant": variant},
            )

        # -------------------------
        # STEP 2: Image count validation
        # -------------------------
        current_gallery_count = variant.images.count()

        # MAIN IMAGE
        if main_file:
            main_after = 1
        elif remove_main:
            main_after = 0
        else:
            main_after = 1 if variant.main_image else 0

        # GALLERY IMAGES
        if gallery_files:
            gallery_after = len(gallery_files)
        elif remove_gallery:
            gallery_after = 0
        else:
            gallery_after = current_gallery_count

        total_images = main_after + gallery_after

        if total_images < 3:
            messages.error(
                request,
                f"Total images must be at least 3. You will have {total_images}."
            )
            return render(
                request,
                "product_management/variant_form.html",
                {"form": form, "action": "Edit", "product": product, "variant": variant},
            )

        if total_images > 7:
            messages.error(
                request,
                f"Total images cannot exceed 7. You will have {total_images}."
            )
            return render(
                request,
                "product_management/variant_form.html",
                {"form": form, "action": "Edit", "product": product, "variant": variant},
            )

        # -------------------------
        # STEP 3: Save variant (no commit)
        # -------------------------
        variant = form.save(commit=False)

        if variant.stock == 0:
            variant.is_listed = False

        # =========================
        # IMAGE HANDLING (FINAL)
        # =========================

        # MAIN IMAGE
        if remove_main and variant.main_image:
            variant.main_image.delete()
            variant.main_image = None

        if main_file:
            if variant.main_image:
                variant.main_image.delete()
            variant.main_image = main_file

        # GALLERY IMAGES
        if gallery_files:
            for img in variant.images.all():
                img.image.delete()
            variant.images.all().delete()

            for idx, img in enumerate(gallery_files):
                VariantImage.objects.create(
                    variant=variant,
                    image=img,
                    order=idx
                )

        elif remove_gallery:
            for img in variant.images.all():
                img.image.delete()
            variant.images.all().delete()

        # AUTO MAIN IMAGE
        if not variant.main_image and variant.images.exists():
            variant.main_image = variant.images.first().image

        # -------------------------
        # STEP 4: Final save
        # -------------------------
        variant.save()
        product.update_stock()

        messages.success(request, "Variant updated successfully.")
        return redirect(
            reverse("custom_admin:product_management:variant_list", args=[product.id])
        )

    else:
        form = VariantForm(instance=variant)

    return render(
        request,
        "product_management/variant_form.html",
        {"form": form, "action": "Edit", "product": product, "variant": variant},
    )




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
        if variant.stock > 0:
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

    # --- SIMILAR ITEMS: Same category products ---
    related_products = (
        Product.objects.filter(
            category=product.category,
            is_deleted=False,
            is_listed=True
        )
        .exclude(id=product.id)
        .prefetch_related("variants__images")
    )

    return render(request, "product_management/product_variant_detail.html", {
        "product": product,
        "variant": selected_variant,
        "variants": variants,
        "related_products": related_products,
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

