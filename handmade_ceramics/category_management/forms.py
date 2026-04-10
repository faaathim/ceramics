# category_management/forms.py

from django import forms
from .models import Category
import re


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'image', 'is_listed']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()

        if not name:
            raise forms.ValidationError("Category name is required.")

        if len(name) < 3:
            raise forms.ValidationError("Name must be at least 3 characters.")

        if len(name) > 150:
            raise forms.ValidationError("Name cannot exceed 150 characters.")

        if not re.match(r'^[A-Za-z0-9 ]+$', name):
            raise forms.ValidationError(
                "Name can only contain letters, numbers, and spaces."
            )

        qs = Category.all_objects.filter(name__iexact=name)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("This category already exists.")

        return name

    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()

        if len(description) > 500:
            raise forms.ValidationError("Description cannot exceed 500 characters.")

        return description

    def clean_image(self):
        image = self.cleaned_data.get('image')

        if image:
            allowed_types = ['image/jpeg', 'image/png', 'image/webp']

            if image.content_type not in allowed_types:
                raise forms.ValidationError(
                    "Only JPG, PNG, and WEBP image formats are allowed."
                )

            valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            if not any(image.name.lower().endswith(ext) for ext in valid_extensions):
                raise forms.ValidationError(
                    "Invalid file extension. Allowed: .jpg, .jpeg, .png, .webp"
                )

            if image.size > 2 * 1024 * 1024:
                raise forms.ValidationError("Image must be less than 2MB.")

        return image


class CategorySearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label='Search',
        widget=forms.TextInput(
            attrs={'placeholder': 'Search by name or description'}
        )
    )