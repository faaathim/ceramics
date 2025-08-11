from django.shortcuts import render, redirect, get_object_or_404
from product.models import Product
from product.forms import ProductForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.views.decorators.cache import never_cache
from admin_panel.views import superuser_required
from PIL import Image
import io
from django.core.files.base import ContentFile
from django.views.decorators.http import require_POST

@never_cache
@superuser_required
def product_list(request):
    query = request.GET.get('q')
    products = Product.objects.filter(is_deleted=False).order_by('-created_at')

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    paginator = Paginator(products, 10)
    page = request.GET.get('page')
    products = paginator.get_page(page)

    return render(request, 'product/product_list.html', {
        'products': products,
        'query': query
    })

@never_cache
@superuser_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            # Validate image file
            image = request.FILES.get('image')
            if image:
                # Check file size (5MB limit)
                if image.size > 5 * 1024 * 1024:
                    messages.error(request, "Image file size must be less than 5MB.")
                    return render(request, 'product/product_form.html', {'form': form, 'title': 'Add Product'})

                # Check file type
                if not image.content_type.startswith('image/'):
                    messages.error(request, "Uploaded file must be an image.")
                    return render(request, 'product/product_form.html', {'form': form, 'title': 'Add Product'})

                # Optional: Server-side resizing
                try:
                    img = Image.open(image)
                    img = img.convert('RGB')  # Ensure image is in RGB format
                    img = img.resize((800, 800), Image.LANCZOS)  # Resize to 800x800 (or your preferred size)
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=85)
                    output.seek(0)
                    # Update the image file in request.FILES
                    form.cleaned_data['image'] = ContentFile(output.read(), name=f"{image.name.split('.')[0]}.jpg")
                except Exception as e:
                    messages.error(request, f"Error processing image: {str(e)}")
                    return render(request, 'product/product_form.html', {'form': form, 'title': 'Add Product'})

            product = form.save()
            messages.success(request, "Product added successfully!")
            return redirect('product_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm()
    return render(request, 'product/product_form.html', {'form': form, 'title': 'Add Product'})

@never_cache
@superuser_required
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            # Validate image file if provided
            image = request.FILES.get('image')
            if image:
                # Check file size (5MB limit)
                if image.size > 5 * 1024 * 1024:
                    messages.error(request, "Image file size must be less than 5MB.")
                    return render(request, 'product/product_form.html', {'form': form, 'title': 'Edit Product'})

                # Check file type
                if not image.content_type.startswith('image/'):
                    messages.error(request, "Uploaded file must be an image.")
                    return render(request, 'product/product_form.html', {'form': form, 'title': 'Edit Product'})

                # Optional: Server-side resizing
                try:
                    img = Image.open(image)
                    img = img.convert('RGB')
                    img = img.resize((800, 800), Image.LANCZOS)
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=85)
                    output.seek(0)
                    form.cleaned_data['image'] = ContentFile(output.read(), name=f"{image.name.split('.')[0]}.jpg")
                except Exception as e:
                    messages.error(request, f"Error processing image: {str(e)}")
                    return render(request, 'product/product_form.html', {'form': form, 'title': 'Edit Product'})

            form.save()
            messages.success(request, "Product updated successfully.")
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'product/product_form.html', {'form': form, 'title': 'Edit Product'})

@superuser_required
@never_cache
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if product.is_deleted:
        return redirect('product_list')
    
    if request.method == 'POST':
        product.is_deleted = True
        product.save()
        messages.success(request, "Product deleted successfully.")
        return redirect('product_list')
    return render(request, 'product/delete_confirm.html', {'product': product})

@never_cache
def product_detail_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    similar_items = Product.objects.filter(
        category=product.category
    ).exclude(pk=product.pk)[:5]

    return render(request, 'product/product_detail.html', {
        'product': product,
        'similar_items': similar_items
    })
