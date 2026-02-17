from django import forms
from .models import ProductOffer, CategoryOffer

class ProductOfferForm(forms.ModelForm):
    class Meta:
        model = ProductOffer
        fields = [
            'product', 'discount_percentage', 'start_date', 'end_date', 'is_active'
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-input'}),
            'discount_percentage': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'max': '90'
            }),
            'start_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-input'},
                format='%Y-%m-%dT%H:%M'
            ),
            'end_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-input'},
                format='%Y-%m-%dT%H:%M'
            ),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox-input'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_date'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['end_date'].input_formats = ['%Y-%m-%dT%H:%M']



class CategoryOfferForm(forms.ModelForm):
    class Meta:
        model = CategoryOffer
        fields = [
            'category', 'discount_percentage', 'start_date', 'end_date', 'is_active'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-input'}),
            'discount_percentage': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'max': '90'
            }),
            'start_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-input'},
                format='%Y-%m-%dT%H:%M'
            ),
            'end_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-input'},
                format='%Y-%m-%dT%H:%M'
            ),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox-input'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_date'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['end_date'].input_formats = ['%Y-%m-%dT%H:%M']