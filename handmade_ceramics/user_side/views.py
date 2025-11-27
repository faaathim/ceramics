from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
from django.db.models import Q
from decimal import Decimal
from user_side.forms import ShopFilterForm
from django.db.models import Prefetch
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache


try:
    from product_management.models import Product, Variant
except Exception:
    Product = None
    Variant = None

try:
    from category_management.models import Category
except Exception:
    Category = None


@never_cache
@login_required(login_url='user_authentication:login')
def home(request):
    products_page = None
    categories = []

    if Product is not None:
        variant_qs = Variant.objects.filter(
            is_deleted=False,
            is_listed=True
        ).order_by('-created_at')

        qs = Product.objects.filter(is_listed=True).prefetch_related(
            Prefetch('variants', queryset=variant_qs, to_attr='listed_variants')
        )

        qs = qs.order_by('-created_at')

        page = request.GET.get('page', 1)
        paginator = Paginator(qs, 8)
        try:
            products_page = paginator.page(page)
        except PageNotAnInteger:
            products_page = paginator.page(1)
        except EmptyPage:
            products_page = paginator.page(paginator.num_pages)

    else:
        products_page = None

    # 👉 Load listed categories
    if Category is not None:
        categories = Category.objects.filter(is_listed=True).order_by('-created_at')[:12]
    else:
        categories = []

    context = {
        'products_page': products_page,
        'categories': categories,
    }
    return render(request, 'user_side/home.html', context)



def shop(request):

    form = ShopFilterForm(request.GET or None)

    if Product is None:
        print("not working")
        return render(request, 'user_side/shop.html', {'form': form, 'products_page': None, 'error': 'Products not available.'})

    # Base queryset: only listed products (your original behavior)
    print("trying to work")
    products_qs = Product.objects.filter(is_listed=True)

    # Prefetch variants (listed ones) to avoid N+1 queries in template:
    if Variant is not None:
        print('yeah its working')
        variants_qs = Variant.objects.filter(is_deleted=False, is_listed=True).order_by('-created_at')
        products_qs = products_qs.prefetch_related(Prefetch('variants', queryset=variants_qs, to_attr='listed_variants'))
    else:
        products_qs = products_qs.prefetch_related('variants')

    # Keep your existing form validation / filters / sorting exactly as-is.
    products_qs_original = products_qs  # keep ref for fallback
    if form.is_valid():
        data = form.cleaned_data
        q = data.get('q')
        cat_id = data.get('category')
        price_min = data.get('price_min')
        price_max = data.get('price_max')
        sort = data.get('sort')

        if q:
            products_qs = products_qs.filter(Q(name__icontains=q) | Q(description__icontains=q))

        if cat_id:
            products_qs = products_qs.filter(category_id=cat_id)

        if price_min is not None:
            from decimal import Decimal
            products_qs = products_qs.filter(price__gte=Decimal(price_min))
        if price_max is not None:
            from decimal import Decimal
            products_qs = products_qs.filter(price__lte=Decimal(price_max))

        if sort == 'price_asc':
            products_qs = products_qs.order_by('price')
        elif sort == 'price_desc':
            products_qs = products_qs.order_by('-price')
        elif sort == 'name_asc':
            products_qs = products_qs.order_by('name')
        elif sort == 'name_desc':
            products_qs = products_qs.order_by('-name')
        elif sort == 'newest':
            products_qs = products_qs.order_by('-created_at')
    else:
        products_qs = products_qs_original

    # Pagination (same as before)
    page = request.GET.get('page', 1)
    paginator = Paginator(products_qs, 12)
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    # Keep current query string for pagination links - helper
    get_copy = request.GET.copy()
    if 'page' in get_copy:
        get_copy.pop('page')
    base_qs = get_copy.urlencode()

    context = {
        'form': form,
        'products_page': products_page,
        'query_string': base_qs,
    }
    return render(request, 'user_side/shop.html', context)

