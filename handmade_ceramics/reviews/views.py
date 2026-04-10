# reviews/views.py

from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Review
from product_management.models import Product
from .utils import can_user_review

@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if not can_user_review(request.user, product):
        messages.error(request, "You cannot review this product.")
        return redirect('custom_admin:product_management:product_detail', pk=product.id)

    if Review.objects.filter(user=request.user, product=product).exists():
        messages.error(request, "You already reviewed this product.")
        return redirect('custom_admin:product_management:product_detail', pk=product.id)

    try:
        rating = int(request.POST.get('rating'))
        if not 1 <= rating <= 5:
            raise ValueError
    except (TypeError, ValueError):
        messages.error(request, "Invalid rating.")
        return redirect('custom_admin:product_management:product_detail', pk=product.id)

    comment = request.POST.get('comment', '').strip()
    if not comment:
        messages.error(request, "Comment cannot be empty.")
        return redirect('custom_admin:product_management:product_detail', pk=product.id)

    Review.objects.create(
        user=request.user,
        product=product,
        rating=rating,
        comment=comment,
        is_approved=True
    )

    messages.success(request, "Review submitted successfully.")
    return redirect('custom_admin:product_management:product_detail', pk=product.id)