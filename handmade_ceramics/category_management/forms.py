# category_management/forms.py

from django import forms
from .models import Category
import re


class CategoryForm(forms.ModelForm):

    class Meta:
        model = Category

        fields = [
            'name',
            'description',
            'is_listed'
        ]

        widgets = {

            'name': forms.TextInput(
                attrs={
                    'placeholder': 'Enter category name',
                    'class': 'form-control',
                    'maxlength': '150',
                }
            ),

            'description': forms.Textarea(
                attrs={
                    'rows': 4,
                    'placeholder': 'Enter category description',
                    'class': 'form-control',
                    'maxlength': '500',
                }
            ),
        }

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

        description = self.cleaned_data.get(
            'description',
            ''
        ).strip()

        # Normalize spaces
        description = " ".join(description.split())

        if description:

            if len(description) < 5:
                raise forms.ValidationError(
                    "Description must contain at least 5 characters."
                )

            if len(description) > 500:
                raise forms.ValidationError(
                    "Description cannot exceed 500 characters."
                )

        return description


class CategorySearchForm(forms.Form):

    q = forms.CharField(
        required=False,
        max_length=100,
        label='Search',

        widget=forms.TextInput(
            attrs={
                'placeholder': 'Search by category name or description',
                'class': 'form-control',
            }
        )
    )

    def clean_q(self):

        q = self.cleaned_data.get('q', '')

        q = " ".join(q.strip().split())

        if len(q) > 100:
            raise forms.ValidationError(
                "Search query is too long."
            )

        return q