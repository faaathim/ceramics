from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404, JsonResponse
from django.db.models import Q

from .models import Product, Variant, VariantImage, product_average_rating, get_related_products
from .forms import ProductForm, ProductSearchForm, VariantForm


# =========================
# AUTH HELPERS
# =========================

def superuser_check(user):
    return user.is_active and user.is_superuser


def admin_required(view_func):
    return login_required(
        user_passes_test(superuser_check, login_url='custom_admin:login')(view_func),
        login_url='custom_admin:login'
    )


# =========================
# PRODUCT VIEWS
# =========================

@admin_required
def product_list(request):
    """Backend search + pagination + optimized queries."""
    form = ProductSearchForm(request.GET or None)

    # ✅ Prefetch variants to avoid N+1 queries
    qs = Product.objects.prefetch_related('variants')

    if form.is_valid():
        q = form.cleaned_data.get('q')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))

    paginator = Paginator(qs, 10)
    page = request.GET.get('page', 1)

    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    return render(request, 'product_management/product_list.html', {
        'form': form,
        'products': products,
        'query': request.GET.get('q', '')
    })


@admin_required
@transaction.atomic
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        main_file = request.FILES.get('main_image')

        if not main_file:
            form.add_error(None, "Main image is required.")
            return render(request, 'product_management/product_form.html', {
                'form': form,
                'action': 'Create',
                'product': None
            })

        if form.is_valid():
            product = form.save(commit=False)
            product.stock = 0
            product.is_listed = False
            product.main_image = main_file
            product.save()

            messages.success(request, f'Product "{product.name}" created. Now add variants.')
            return redirect(reverse('custom_admin:product_management:variant_list', args=[product.id]))

    else:
        form = ProductForm()

    return render(request, 'product_management/product_form.html', {
        'form': form,
        'action': 'Create',
        'product': None
    })


@admin_required
@transaction.atomic
def product_edit(request, pk):
    product = get_object_or_404(Product.all_objects, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        main_file = request.FILES.get("main_image")
        remove_main = "remove_main_image" in request.POST

        if form.is_valid():
            product = form.save(commit=False)

            if remove_main:
                product.main_image = None

            if main_file:
                product.main_image = main_file

            product.save()

            messages.success(request, "Product updated successfully!")
            return redirect("custom_admin:product_management:product_list")

    else:
        form = ProductForm(instance=product)

    return render(request, "product_management/product_edit.html", {
        "form": form,
        "product": product
    })


@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product.all_objects, pk=pk)

    if request.method == 'POST':
        product.is_deleted = True
        product.save()
        messages.success(request, f'Product "{product.name}" deleted successfully.')

    return redirect(reverse('custom_admin:product_management:product_list'))


@admin_required
def product_toggle_listing(request, pk):
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


# =========================
# VARIANT VIEWS
# =========================

@admin_required
def variant_list(request, product_pk):
    product = get_object_or_404(Product.all_objects, pk=product_pk)

    if product.is_deleted:
        messages.error(request, "Product not available.")
        return redirect(reverse('custom_admin:product_management:product_list'))

    q = request.GET.get('q', '').strip()

    # ✅ Prefetch images for performance
    qs = product.variants.filter(is_deleted=False).prefetch_related('images')

    if q:
        qs = qs.filter(color__icontains=q)

    paginator = Paginator(qs, 10)
    page = request.GET.get('page', 1)

    try:
        variants = paginator.page(page)
    except PageNotAnInteger:
        variants = paginator.page(1)
    except EmptyPage:
        variants = paginator.page(paginator.num_pages)

    return render(request, 'product_management/variant_list.html', {
        'product': product,
        'variants': variants,
        'query': q
    })


@admin_required
@transaction.atomic
def variant_create(request, product_pk):
    product = get_object_or_404(Product.all_objects, pk=product_pk)

    if request.method == 'POST':
        form = VariantForm(request.POST)
        gallery_files = request.FILES.getlist('images')

        total_images = len(gallery_files)

        if total_images < 3:
            messages.error(request, "Please upload at least 3 images.")
            return render(request, 'product_management/variant_form.html', {
                'form': form,
                'action': 'Create',
                'product': product
            })

        if total_images > 7:
            messages.error(request, "Max 7 images allowed.")
            return render(request, 'product_management/variant_form.html', {
                'form': form,
                'action': 'Create',
                'product': product
            })

        if form.is_valid():
            variant = form.save(commit=False)
            variant.product = product

            if variant.stock == 0:
                variant.is_listed = False

            variant.save()

            for idx, img in enumerate(gallery_files):
                VariantImage.objects.create(
                    variant=variant,
                    image=img,
                    order=idx
                )

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
        form = VariantForm(request.POST, instance=variant)
        gallery_files = request.FILES.getlist("images")
        remove_gallery = request.POST.get("remove_gallery_images") == "1"

        if not form.is_valid():
            messages.error(request, "Fix errors.")
            return render(request, "product_management/variant_form.html", {
                "form": form,
                "product": product,
                "variant": variant
            })

        variant = form.save(commit=False)

        if variant.stock == 0:
            variant.is_listed = False

        # ✅ Proper Cloudinary cleanup
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

        variant.save()
        product.update_stock()

        messages.success(request, "Variant updated.")
        return redirect(
            reverse("custom_admin:product_management:variant_list", args=[product.id])
        )

    else:
        form = VariantForm(instance=variant)

    return render(request, "product_management/variant_form.html", {
        "form": form,
        "product": product,
        "variant": variant
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
        return redirect(
            reverse('custom_admin:product_management:variant_list', args=[product.id])
        )

    return render(request, 'product_management/confirm_delete_variant.html', {
        'product': product,
        'variant': variant
    })


@admin_required
def variant_toggle_listing(request, product_pk, pk):
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
            messages.error(request, 'Cannot list variant with 0 stock.')

    return redirect(
        reverse('custom_admin:product_management:variant_list', args=[product.id])
    )


# =========================
# FRONTEND VIEWS
# =========================

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_deleted=False)

    variants = product.variants.filter(
        is_deleted=False,
        is_listed=True
    ).prefetch_related("images")

    if not variants.exists():
        raise Http404("No variants available.")

    variant_id = request.GET.get("variant")

    if variant_id:
        try:
            selected_variant = variants.get(id=variant_id)
        except Variant.DoesNotExist:
            selected_variant = variants.first()
    else:
        selected_variant = variants.first()

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
    variant = get_object_or_404(
        Variant,
        id=variant_id,
        is_deleted=False,
        is_listed=True
    )

    first_image = variant.images.first()

    data = {
        "id": variant.id,
        "color": variant.color,
        "stock": variant.stock,
        "image": first_image.image.url if first_image else "",
    }

    return JsonResponse(data)