from django import forms
from django.db.models import Q

from .models import Product, Variant
from category_management.models import Category


# =========================
# PRODUCT FORM
# =========================

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'price', 'main_image', 'is_listed']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ Only active categories
        self.fields['category'].queryset = Category.objects.filter(is_listed=True)

        # ✅ Allow previously selected inactive category (edit case)
        if self.instance.pk and self.instance.category:
            self.fields['category'].queryset = Category.objects.filter(
                Q(is_listed=True) | Q(pk=self.instance.category.pk)
            )

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is None or price <= 0:
            raise forms.ValidationError("Price must be a positive number.")
        return price


# =========================
# PRODUCT SEARCH FORM
# =========================

class ProductSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label='Search',
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by name or description'
        })
    )


# =========================
# VARIANT FORM
# =========================

class VariantForm(forms.ModelForm):
    class Meta:
        model = Variant
        # ❌ REMOVED main_image
        fields = ['color', 'stock', 'is_listed']
        widgets = {
            'color': forms.TextInput(attrs={
                'placeholder': 'Color (e.g., Matte Black, White, Terracotta)'
            }),
        }

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is None or stock < 0:
            raise forms.ValidationError("Stock must be 0 or greater.")
        return stock

    def clean_color(self):
        color = self.cleaned_data.get('color')

        if not color:
            raise forms.ValidationError("Color is required.")

        # ✅ Normalize (avoid duplicates like 'Red' vs 'red')
        return color.strip().title()