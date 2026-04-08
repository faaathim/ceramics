from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.urls import reverse

from product_management.models import Variant
from .models import Wishlist
from profiles.models import Profile


@login_required
def add_to_wishlist(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request")

    try:
        variant_id = int(request.POST.get('variant_id'))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("Invalid variant id")

    variant = get_object_or_404(
        Variant,
        pk=variant_id,
        is_deleted=False,
        is_listed=True
    )

    # 🔒 Extra safety
    if variant.stock <= 0:
        return HttpResponseBadRequest("Variant out of stock")

    Wishlist.objects.get_or_create(
        user=request.user,
        variant=variant
    )

    return redirect(request.META.get('HTTP_REFERER', '/'))



@login_required
def remove_from_wishlist(request, variant_id):
    Wishlist.objects.filter(
        user=request.user,
        variant_id=variant_id
    ).delete()

    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def wishlist_page(request):
    items = (
        Wishlist.objects
        .filter(user=request.user)
        .select_related('variant__product')
    )
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        profile = None

    return render(request, 'wishlist/wishlist_page.html', {
        'items': items,
        'profile':profile
    })
