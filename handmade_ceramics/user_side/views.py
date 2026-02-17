from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Prefetch
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache

from user_side.forms import ShopFilterForm

from product_management.models import Product, Variant
from category_management.models import Category
from wishlist.models import Wishlist  # Add this import


# ======================================================
# HOME PAGE
# ======================================================
@never_cache
@login_required(login_url='user_authentication:login')
def home(request):

    # Only valid, visible variants
    listed_variants_qs = Variant.objects.filter(
        is_listed=True,
        is_deleted=False
    ).order_by('-created_at')

    # Only valid, visible products
    products_qs = (
        Product.objects.filter(
            is_listed=True,
            category__is_listed=True,
            variants__is_listed=True,
            variants__is_deleted=False
        )
        .prefetch_related(
            Prefetch(
                'variants',
                queryset=listed_variants_qs,
                to_attr='listed_variants'
            )
        )
        .distinct()
        .order_by('-created_at')
    )

    paginator = Paginator(products_qs, 8)
    page = request.GET.get('page', 1)

    try:
        products_page = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        products_page = paginator.page(1)

    categories = Category.objects.filter(
        is_listed=True
    ).order_by('-created_at')[:12]

    # Get wishlist variant IDs for authenticated users
    wishlist_variant_ids = []
    if request.user.is_authenticated:
        wishlist_variant_ids = list(
            Wishlist.objects.filter(user=request.user)
            .values_list('variant_id', flat=True)
        )

    return render(request, 'user_side/home.html', {
        'products_page': products_page,
        'categories': categories,
        'wishlist_variant_ids': wishlist_variant_ids,  # Add this
    })


# ======================================================
# SHOP PAGE
# ======================================================
def shop(request):

    form = ShopFilterForm(request.GET or None)

    # Only valid, visible variants (same as home)
    listed_variants_qs = Variant.objects.filter(
        is_listed=True,
        is_deleted=False
    ).order_by('-created_at')

    # Base queryset (same rules as home)
    products_qs = Product.objects.filter(
        is_listed=True,
        category__is_listed=True,
        variants__is_listed=True,
        variants__is_deleted=False
    ).distinct()

    # Prefetch only valid variants BEFORE filtering
    products_qs = products_qs.prefetch_related(
        Prefetch(
            'variants',
            queryset=listed_variants_qs,
            to_attr='listed_variants'
        )
    )

    # ---------------- FILTERS ----------------
    if form.is_valid():
        data = form.cleaned_data

        if data.get('q'):
            products_qs = products_qs.filter(
                Q(name__icontains=data['q']) |
                Q(description__icontains=data['q'])
            )

        if data.get('category'):
            products_qs = products_qs.filter(
                category_id=data['category']
            )

        if data.get('price_min') is not None:
            products_qs = products_qs.filter(
                price__gte=data['price_min']
            )

        if data.get('price_max') is not None:
            products_qs = products_qs.filter(
                price__lte=data['price_max']
            )

        sort = data.get('sort')
        if sort == 'price_asc':
            products_qs = products_qs.order_by('price')
        elif sort == 'price_desc':
            products_qs = products_qs.order_by('-price')
        elif sort == 'name_asc':
            products_qs = products_qs.order_by('name')
        elif sort == 'name_desc':
            products_qs = products_qs.order_by('-name')
        else:
            products_qs = products_qs.order_by('-created_at')

    # ---------------- PAGINATION ----------------
    paginator = Paginator(products_qs, 12)
    page = request.GET.get('page', 1)

    try:
        products_page = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        products_page = paginator.page(1)

    # Preserve filters in pagination
    query_params = request.GET.copy()
    query_params.pop('page', None)

    # Get wishlist variant IDs for authenticated users
    wishlist_variant_ids = []
    if request.user.is_authenticated:
        wishlist_variant_ids = list(
            Wishlist.objects.filter(user=request.user)
            .values_list('variant_id', flat=True)
        )

    return render(request, 'user_side/shop.html', {
        'form': form,
        'products_page': products_page,
        'query_string': query_params.urlencode(),
        'wishlist_variant_ids': wishlist_variant_ids,  # Add this
    })