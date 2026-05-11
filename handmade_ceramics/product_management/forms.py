from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.core.files.uploadedfile import UploadedFile
from .models import Product, Variant
from category_management.models import Category


class ProductForm(forms.ModelForm):
    main_image = forms.ImageField(required=False)

    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'price', 'main_image', 'is_listed']

    def __init__(self, *args, **kwargs):
        # pop the flag before super().__init__ touches kwargs
        self.remove_main = kwargs.pop("remove_main", False)
        super().__init__(*args, **kwargs)

        active_qs = Category.objects.filter(is_listed=True)

        if self.instance.pk and self.instance.category_id:
            # always include the product's current category even if unlisted
            active_qs = Category.objects.filter(
                Q(is_listed=True) | Q(pk=self.instance.category_id)
            )

        self.fields['category'].queryset = active_qs

    def clean_is_listed(self):
        # Unchecked checkboxes send nothing, so default to False
        return self.cleaned_data.get('is_listed', False)

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 3:
            raise forms.ValidationError("Product name must contain at least 3 characters.")
        if Product.all_objects.filter(
            name__iexact=name, is_deleted=False,
        ).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A product with this name already exists.")
        return name.title()

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is None:
            raise forms.ValidationError("Price is required.")
        if price <= 0:
            raise forms.ValidationError("Price must be greater than zero.")
        if price > 100000:
            raise forms.ValidationError("Price is too high.")
        return price

    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        if len(description) < 20:
            raise forms.ValidationError("Description must contain at least 20 characters.")
        return description

    def clean_main_image(self):
        # Get the image — fall back to raw files dict if cleaned_data missed it
        image = self.cleaned_data.get('main_image') or self.files.get('main_image')

        VALID_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']
        VALID_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp']

        is_edit = bool(self.instance.pk)

        if is_edit:
            has_existing = bool(
                self.instance.main_image
                and getattr(self.instance.main_image, 'public_id', None)  # Cloudinary-safe check
            )

            if self.remove_main and not image:
                raise forms.ValidationError(
                    "You removed the current image. Please upload a replacement."
                )

            if not has_existing and not image:
                raise forms.ValidationError(
                    "This product has no image. Please upload a main product image."
                )

        else:
            # CREATE — always required
            if not image:
                raise forms.ValidationError("Main product image is required.")

        # Validate the uploaded file
        if image and isinstance(image, UploadedFile):
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image size must be below 5 MB.")

            ext = image.name.rsplit('.', 1)[-1].lower()
            mime = getattr(image, 'content_type', '').lower()

            if ext not in VALID_EXTENSIONS:
                raise forms.ValidationError(
                    f'"{image.name}" has an unsupported format. Only JPG, PNG, and WEBP are allowed.'
                )
            if mime and mime not in VALID_MIME_TYPES:
                raise forms.ValidationError(
                    f'"{image.name}" has an unsupported format. Only JPG, PNG, and WEBP are allowed.'
                )

        return image  # return the file so Django/Cloudinary can process it

    def clean(self):
        cleaned_data = super().clean()
        is_listed = cleaned_data.get('is_listed')
        if is_listed and self.instance.pk:
            if not self.instance.can_be_listed():
                self.add_error('is_listed', "Product must have at least one listed variant.")
        return cleaned_data

class ProductSearchForm(forms.Form):
    q = forms.CharField(required=False)


class VariantForm(forms.ModelForm):

    class Meta:
        model   = Variant
        fields  = ['color', 'stock', 'is_listed']

    def clean_color(self):
        color = self.cleaned_data.get('color', '').strip()

        if len(color) < 2:
            raise forms.ValidationError("Color name is too short.")

        color   = color.title()
        product = (
            self.instance.product
            if self.instance.pk
            else self.initial.get('product')
        )

        if product:
            exists = Variant.objects.filter(
                product=product,
                color__iexact=color,
                is_deleted=False,
            ).exclude(pk=self.instance.pk).exists()

            if exists:
                raise forms.ValidationError("This color variant already exists.")

        return color

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')

        if stock is None:
            raise forms.ValidationError("Stock value is required.")

        if stock < 0:
            raise forms.ValidationError("Stock cannot be negative.")

        if stock > 10000:
            raise forms.ValidationError("Stock value is too large.")

        return stock

    def clean(self):
        cleaned_data = super().clean()
        stock        = cleaned_data.get('stock')
        is_listed    = cleaned_data.get('is_listed')

        if stock == 0 and is_listed:
            self.add_error('is_listed', "Cannot list variant with zero stock.")

        return cleaned_data