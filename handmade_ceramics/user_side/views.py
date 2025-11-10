from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
from django.db.models import Q
from decimal import Decimal
from user_side.forms import ShopFilterForm


try:
    from product_management.models import Product
except Exception:
    Product = None

try:
    from category_management.models import Category
except Exception:
    Category = None

def home(request):
    products_page = None
    categories = []

    if Product is not None:
        qs = Product.objects.filter(is_listed=True)  
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
    """
    Product listing with backend search, filter, sort, pagination.
    All input comes via GET; we use ShopFilterForm to validate/clean.
    """
    # bind GET to form so validation runs
    form = ShopFilterForm(request.GET or None)

    products_qs = Product.objects.none() if Product is None else Product.objects.filter(is_listed=True)  # manager excludes is_deleted

    if Product is None:
        # Product model missing, render friendly message
        return render(request, 'user_side/shop.html', {'form': form, 'products_page': None, 'error': 'Products not available.'})

    if form.is_valid():
        data = form.cleaned_data
        q = data.get('q')
        cat_id = data.get('category')
        price_min = data.get('price_min')
        price_max = data.get('price_max')
        sort = data.get('sort')

        # Search: name or description (case-insensitive)
        if q:
            products_qs = products_qs.filter(Q(name__icontains=q) | Q(description__icontains=q))

        # Category filter
        if cat_id:
            products_qs = products_qs.filter(category_id=cat_id)

        # Price range filter
        if price_min is not None:
            products_qs = products_qs.filter(price__gte=Decimal(price_min))
        if price_max is not None:
            products_qs = products_qs.filter(price__lte=Decimal(price_max))

        # Sorting
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
        # else default ordering from model (newest first)
    else:
        # invalid form data -> ignore filters and show default queryset
        products_qs = Product.objects.filter(is_listed=True)

    # BACKEND pagination, 12 per page
    page = request.GET.get('page', 1)
    paginator = Paginator(products_qs, 12)
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    # keep current query string for pagination links - helper
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
