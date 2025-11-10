from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'price', 'stock', 'is_listed']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is None or price <= 0:
            raise forms.ValidationError("Price must be a positive number.")
        return price

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is None or stock <= 0:
            raise forms.ValidationError("Stock must be greater than 0.")
        return stock

class ProductSearchForm(forms.Form):
    q = forms.CharField(required=False, label='Search', widget=forms.TextInput(attrs={'placeholder': 'Search by name or description'}))
