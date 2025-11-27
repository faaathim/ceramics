# product_management/forms.py
from django import forms
from .models import Product, Variant

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'price', 'main_image', 'is_listed']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    # stock is not in fields anymore (read-only/computed)

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is None or price <= 0:
            raise forms.ValidationError("Price must be a positive number.")
        return price

class ProductSearchForm(forms.Form):
    q = forms.CharField(required=False, label='Search', widget=forms.TextInput(attrs={'placeholder': 'Search by name or description'}))


class VariantForm(forms.ModelForm):
    class Meta:
        model = Variant
        fields = ['color', 'stock', 'is_listed', 'main_image']
        widgets = {
            'color': forms.TextInput(attrs={'placeholder': 'Color / label'}),
        }

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is None or stock < 0:
            raise forms.ValidationError("Stock must be 0 or greater.")
        return stock
