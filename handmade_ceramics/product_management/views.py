from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404, JsonResponse
from django.db.models import Q

from reviews.utils import can_user_review
from .models import Product, Variant, VariantImage
from .forms import ProductForm, ProductSearchForm, VariantForm


def superuser_check(user):
    return user.is_active and user.is_superuser


def admin_required(view_func):
    return login_required(
        user_passes_test(superuser_check, login_url='custom_admin:login')(view_func),
        login_url='custom_admin:login'
    )


@admin_required
def product_list(request):
    form = ProductSearchForm(request.GET or None)
    qs = Product.objects.prefetch_related('variants')

    if form.is_valid():
        q = form.cleaned_data.get('q')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))

    paginator = Paginator(qs, 10)
    page = request.GET.get('page', 1)

    try:
        products = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        products = paginator.page(1)

    return render(request, 'product_management/product_list.html', {
        'form': form,
        'products': products,
        'query': request.GET.get('q', '')
    })


@admin_required
@transaction.atomic
def product_create(request):
    if request.method == 'POST':
        print("request is submitting")
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            product = form.save(commit=False)
            product.stock = 0
            product.is_listed = False
            product.save()

            messages.success(request, f'Product "{product.name}" created.')
            return redirect(
                reverse('custom_admin:product_management:variant_list', args=[product.id])
            )
    else:
        form = ProductForm()

    return render(request, 'product_management/product_form.html', {
        'form': form,
        'action': 'Create',
        'product': None,
    })


@admin_required
@transaction.atomic
def product_edit(request, pk):
    product = get_object_or_404(Product.all_objects, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        remove_main = "remove_main_image" in request.POST

        if form.is_valid():
            product = form.save(commit=False)

            if remove_main and not request.FILES.get("main_image"):
                if product.main_image:
                    product.main_image.delete(save=False)
                product.main_image = None

            product.save()

            messages.success(request, "Product updated successfully!")
            return redirect("custom_admin:product_management:product_list")

    else:
        form = ProductForm(instance=product)

    return render(request, "product_management/product_edit.html", {
        "form": form,
        "product": product,
    })


@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product.all_objects, pk=pk)

    if request.method == 'POST':
        product.is_deleted = True
        product.save()
        messages.success(request, f'Product "{product.name}" deleted.')

    return redirect(reverse('custom_admin:product_management:product_list'))


@admin_required
def product_toggle_listing(request, pk):
    product = get_object_or_404(Product.all_objects, pk=pk)

    if request.method == 'POST':
        if product.can_be_listed():
            product.is_listed = not product.is_listed
            product.save()

            status = "listed" if product.is_listed else "unlisted"
            messages.success(request, f'Product "{product.name}" {status}.')
        else:
            messages.error(request, "Add listed variants first.")

    return redirect(reverse('custom_admin:product_management:product_list'))


@admin_required
def variant_list(request, product_pk):
    product = get_object_or_404(Product.all_objects, pk=product_pk)

    qs = product.variants.filter(is_deleted=False).prefetch_related('images')

    paginator = Paginator(qs, 10)
    page = request.GET.get('page', 1)

    try:
        variants = paginator.page(page)
    except:
        variants = paginator.page(1)

    return render(request, 'product_management/variant_list.html', {
        'product': product,
        'variants': variants,
    })


@admin_required
@transaction.atomic
def variant_create(request, product_pk):
    product = get_object_or_404(Product.all_objects, pk=product_pk)

    if request.method == 'POST':
        form = VariantForm(request.POST)
        images = request.FILES.getlist('images')

        if form.is_valid():
            if len(images) < 3:
                form.add_error(None, "Minimum 3 images required.")
            elif len(images) > 7:
                form.add_error(None, "Max 7 images allowed.")
            else:
                variant = form.save(commit=False)
                variant.product = product
                variant.save()

                for i, img in enumerate(images):
                    VariantImage.objects.create(variant=variant, image=img, order=i)

                product.update_stock()

                messages.success(request, "Variant created.")
                return redirect(
                    reverse('custom_admin:product_management:variant_list', args=[product.id])
                )

    else:
        form = VariantForm(initial={'product': product})

    return render(request, 'product_management/variant_form.html', {
        'form': form,
        'product': product
    })


@admin_required
def variant_delete_confirm(request, product_pk, pk):
    product = get_object_or_404(Product.all_objects, pk=product_pk)
    variant = get_object_or_404(Variant, pk=pk, product=product)

    if request.method == 'POST':
        variant.is_deleted = True
        variant.save()
        product.update_stock()

        messages.success(request, "Variant deleted.")
        return redirect(
            reverse('custom_admin:product_management:variant_list', args=[product.id])
        )

    return render(request, 'product_management/confirm_delete_variant.html', {
        'product': product,
        'variant': variant
    })


@admin_required
def variant_toggle_listing(request, product_pk, pk):
    variant = get_object_or_404(Variant, pk=pk, product_id=product_pk)

    if request.method == 'POST':
        if variant.stock > 0:
            variant.is_listed = not variant.is_listed
            variant.save()
            messages.success(request, "Variant updated.")
        else:
            messages.error(request, "Stock is zero.")

    return redirect(
        reverse('custom_admin:product_management:variant_list', args=[product_pk])
    )


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_deleted=False)

    variants = product.variants.filter(is_deleted=False, is_listed=True)

    if not variants.exists():
        raise Http404

    selected_variant = variants.first()

    return render(request, "product_management/product_variant_detail.html", {
        "product": product,
        "variant": selected_variant,
        "variants": variants,
    })


def variant_json(request, variant_id):
    variant = get_object_or_404(Variant, id=variant_id, is_deleted=False, is_listed=True)

    image = variant.images.first()

    return JsonResponse({
        "id": variant.id,
        "color": variant.color,
        "stock": variant.stock,
        "image": image.image.url if image else "",
    })


@admin_required
@transaction.atomic
def variant_edit(request, product_pk, pk):
    product = get_object_or_404(Product.all_objects, pk=product_pk)
    variant = get_object_or_404(Variant, pk=pk, product=product)

    if request.method == "POST":
        form = VariantForm(request.POST, instance=variant)
        images = request.FILES.getlist("images")
        remove_gallery = request.POST.get("remove_gallery_images") == "1"

        if form.is_valid():
            variant = form.save(commit=False)

            if images:
                variant.images.all().delete()
                for i, img in enumerate(images):
                    VariantImage.objects.create(
                        variant=variant,
                        image=img,
                        order=i
                    )

            elif remove_gallery:
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