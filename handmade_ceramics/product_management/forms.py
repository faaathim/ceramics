# product_management/forms.py

from django import forms
from django.db.models import Q
import re
from .models import Product, Variant
from category_management.models import Category



class ProductForm(forms.ModelForm):
    main_image = forms.ImageField(required=False)

    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'price', 'main_image', 'is_listed']

    def __init__(self, *args, **kwargs):
        self.remove_main = kwargs.pop("remove_main", False)
        super().__init__(*args, **kwargs)

        self.fields['category'].queryset = Category.objects.filter(is_listed=True)

        if self.instance.pk and self.instance.category:
            self.fields['category'].queryset = Category.objects.filter(
                Q(is_listed=True) | Q(pk=self.instance.category.pk)
            )

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.remove_main:
            instance.main_image = None

        if commit:
            instance.save()

        return instance

    def clean_name(self):

        name = self.cleaned_data.get('name', '')

        # Remove leading/trailing spaces
        name = name.strip()

        # Remove multiple internal spaces
        name = " ".join(name.split())

        # Empty validation
        if not name:
            raise forms.ValidationError(
                "Category name is required."
            )

        # Minimum length
        if len(name) < 3:
            raise forms.ValidationError(
                "Category name must contain at least 3 characters."
            )

        # Maximum length
        if len(name) > 150:
            raise forms.ValidationError(
                "Category name cannot exceed 150 characters."
            )

        # Prevent numeric-only names
        if name.isdigit():
            raise forms.ValidationError(
                "Category name cannot contain only numbers."
            )

        # Allow only letters, numbers, spaces, hyphen, ampersand
        if not re.match(r'^[A-Za-z0-9 &-]+$', name):
            raise forms.ValidationError(
                "Only letters, numbers, spaces, '&' and '-' are allowed."
            )

        # Duplicate check
        qs = Category.all_objects.filter(
            name__iexact=name
        )

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                "A category with this name already exists."
            )

        return name
    
    def clean_description(self):
        description = self.cleaned_data.get('description', '')

        # Remove leading/trailing spaces
        description = description.strip()

        # Normalize multiple spaces
        description = " ".join(description.split())

        if description:

            # Length checks
            if len(description) < 5:
                raise forms.ValidationError(
                    "Description must contain at least 5 characters."
                )

            if len(description) > 500:
                raise forms.ValidationError(
                    "Description cannot exceed 500 characters."
                )

            # Allow letters, numbers, spaces, and basic punctuation only
            # Blocks emojis, weird symbols, control characters, etc.
            if not re.match(r'^[A-Za-z0-9 .,\'"-]+$', description):
                raise forms.ValidationError(
                    "Description contains invalid characters. Only letters, numbers, spaces, and basic punctuation (.,'\"-) are allowed."
                )

            # Prevent too many special characters (spam-like input)
            special_count = len(re.findall(r'[^\w\s]', description))
            if special_count > 10:
                raise forms.ValidationError(
                    "Description contains too many special characters."
                )

        return description

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

        color = color.strip()

        # Only letters allowed (no numbers, spaces, symbols)
        if not re.match(r'^[A-Za-z]+$', color):
            raise forms.ValidationError("Color must contain only letters.")

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
    
    