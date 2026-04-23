from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404, JsonResponse
from django.db.models import Q, Max

from reviews.utils import can_user_review
from reviews.models import Review
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
        form = VariantForm(request.POST, request.FILES)
        
        main_image = request.FILES.get('main_image')
        gallery_images = request.FILES.getlist('images')
        
        all_images = []
        if main_image:
            all_images.append(main_image)
        all_images.extend(gallery_images)

        if form.is_valid():
            if len(all_images) < 3:
                form.add_error(None, "Minimum 3 images required.")
            elif len(all_images) > 7:
                form.add_error(None, "Max 7 images allowed.")
            else:
                variant = form.save(commit=False)
                variant.product = product
                variant.save()

                for i, img in enumerate(all_images):
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
    
    # Check for requested variant
    variant_id = request.GET.get('variant')
    if variant_id:
        v_obj = variants.filter(id=variant_id).first()
        if v_obj:
            selected_variant = v_obj

    reviews = Review.objects.filter(product=product).select_related('user').order_by('-created_at')
    
    can_review = False
    if request.user.is_authenticated:
        # User can review if they purchased it AND haven't reviewed it yet
        already_reviewed = reviews.filter(user=request.user).exists()
        if can_user_review(request.user, product) and not already_reviewed:
            can_review = True

    return render(request, "product_management/product_variant_detail.html", {
        "product": product,
        "variant": selected_variant,
        "variants": variants,
        "reviews": reviews,
        "can_review": can_review,
        "already_reviewed": already_reviewed if request.user.is_authenticated else False,
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
        form = VariantForm(request.POST, request.FILES, instance=variant)
        new_main_image = request.FILES.get('main_image')
        new_gallery_images = request.FILES.getlist("images")
        
        remove_main = request.POST.get("remove_main_image") == "1"
        remove_gallery = request.POST.get("remove_gallery_images") == "1"
        remove_gallery_ids_str = request.POST.get("remove_gallery_ids", "")

        if form.is_valid():
            # Calculate final image count
            current_main_count = 1 if variant.images.filter(order=0).exists() else 0
            current_gallery_count = variant.images.filter(order__gt=0).count()
            
            final_main_count = 1 if new_main_image else (0 if remove_main else current_main_count)
            
            remove_ids = [int(i.strip()) for i in remove_gallery_ids_str.split(',') if i.strip().isdigit()]
            deleted_gallery_count = 0
            if remove_gallery:
                deleted_gallery_count = current_gallery_count
            elif remove_ids:
                deleted_gallery_count = variant.images.filter(order__gt=0, id__in=remove_ids).count()
                
            final_gallery_count = current_gallery_count - deleted_gallery_count + len(new_gallery_images)
            total_final_images = final_main_count + final_gallery_count
            
            if total_final_images < 3 and total_final_images < (current_main_count + current_gallery_count):
                form.add_error(None, "Minimum 3 images required.")
            elif total_final_images > 7:
                form.add_error(None, "Max 7 images allowed.")
            else:
                variant = form.save()

                if remove_gallery:
                    variant.images.filter(order__gt=0).delete()
                elif remove_ids:
                    variant.images.filter(order__gt=0, id__in=remove_ids).delete()

                if remove_main:
                    variant.images.filter(order=0).delete()

                # Handle new main image
                if new_main_image:
                    first_img = variant.images.filter(order=0).first()
                    if first_img:
                        first_img.image = new_main_image
                        first_img.save()
                    else:
                        VariantImage.objects.create(variant=variant, image=new_main_image, order=0)

                # Append new gallery images
                if new_gallery_images:
                    current_max_order = variant.images.aggregate(Max('order'))['order__max']
                    start_order = 1 if current_max_order is None else current_max_order + 1
                    for i, img in enumerate(new_gallery_images):
                        VariantImage.objects.create(variant=variant, image=img, order=start_order + i)

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