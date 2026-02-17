from django.contrib import admin
from offers.models import ProductOffer, CategoryOffer


@admin.register(ProductOffer)
class ProductOfferAdmin(admin.ModelAdmin):
    list_display = (
        'product',
        'discount_percentage',
        'is_active',
        'start_date',
        'end_date',
        'created_at'
    )
    list_filter = ('is_active',)
    search_fields = ('product__name',)


@admin.register(CategoryOffer)
class CategoryOfferAdmin(admin.ModelAdmin):
    list_display = (
        'category',
        'discount_percentage',
        'is_active',
        'start_date',
        'end_date',
        'created_at'
    )
    list_filter = ('is_active',)
    search_fields = ('category__name',)
