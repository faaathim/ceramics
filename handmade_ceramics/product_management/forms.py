# product_management/forms.py

from django import forms
from django.db.models import Q

from .models import Product, Variant
from category_management.models import Category


# =========================
# PRODUCT FORM
# =========================

class ProductForm(forms.ModelForm):
    main_image = forms.ImageField(required=False)

    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'price', 'main_image', 'is_listed']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['category'].queryset = Category.objects.filter(is_listed=True)

        if self.instance.pk and self.instance.category:
            self.fields['category'].queryset = Category.objects.filter(
                Q(is_listed=True) | Q(pk=self.instance.category.pk)
            )

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name or len(name.strip()) < 3:
            raise forms.ValidationError("Minimum 3 characters required.")
        return name.strip()

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is None or price <= 0:
            raise forms.ValidationError("Enter a valid price.")
        return price

    def clean_main_image(self):
        image = self.cleaned_data.get('main_image')

        if not self.instance.pk and not image:
            raise forms.ValidationError("Main image is required.")

        return image


# =========================
# SEARCH FORM
# =========================

class ProductSearchForm(forms.Form):
    q = forms.CharField(required=False)


# =========================
# VARIANT FORM
# =========================

class VariantForm(forms.ModelForm):

    class Meta:
        model = Variant
        fields = ['color', 'stock', 'is_listed']

    def clean_color(self):
        color = self.cleaned_data.get('color')

        if not color:
            raise forms.ValidationError("Color required.")

        color = color.strip().title()

        product = self.instance.product if self.instance.pk else self.initial.get('product')

        if product:
            if Variant.objects.filter(
                product=product,
                color__iexact=color,
                is_deleted=False
            ).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("Color already exists.")

        return color

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')

        if stock is None or stock < 0:
            raise forms.ValidationError("Stock must be >= 0.")

        return stock

    def clean(self):
        cleaned_data = super().clean()

        stock = cleaned_data.get('stock')
        is_listed = cleaned_data.get('is_listed')

        if stock == 0 and is_listed:
            self.add_error('is_listed', "Cannot list with zero stock.")

        return cleaned_data