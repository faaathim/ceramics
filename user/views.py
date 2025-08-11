from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from product.models import Product
from category.models import Category
from django.views.decorators.cache import never_cache

# Create your views here.

# view for home page


@never_cache
def home(request):
    new_arrivals = Product.objects.filter(is_listed=True, is_deleted=False).order_by('-created_at')[:10]
    return render(request, 'user/home.html', {'new_arrivals': new_arrivals})


# view for shop

@never_cache
def shop(request):
    products = Product.objects.filter(is_deleted=False, is_listed=True)
    categories = Category.objects.filter(is_deleted=False, is_listed=True)

    query = request.GET.get('q', '')
    category_filter = request.GET.get('category')
    price_filter = request.GET.get('price')
    sort_by = request.GET.get('sort')

    min_price = None
    max_price = None

    #search
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    # category filter
    if category_filter:
        products = products.filter(category__id=category_filter)

    # price filter
    if price_filter:
        try:
            min_price, max_price = map(int, price_filter.split('-'))
            products = products.filter(price__gte=min_price, price__lte=max_price).distinct()
        except ValueError:
            min_price = None
            max_price = None

    # sort
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price__desc':
        products = products.order_by('-price')
    elif sort_by == 'name_asc':
        products = products.order_by('name')
    elif sort_by == 'name_desc':
        products = products.order_by('-name')

    # pagination
    paginator = Paginator(products.distinct(), 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    price_ranges = {
        "100 - 300": (100, 300),
        "300 - 500": (300, 500),
        "500 - 1000": (500, 1000),
        "1000 - 2000": (1000, 2000),
        "Above 2000": (2000, 100000),
    }

    return render(request, 'user/shop.html', {
        'products': page_obj,
        'categories': categories,
        'query': query,
        'category_filter': category_filter,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
    })