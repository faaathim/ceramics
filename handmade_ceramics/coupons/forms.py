from django import forms
from .models import Coupon


class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = [
            'code',
            'discount_percentage',
            'min_order_amount',
            'expiry_date',
            'is_active'
        ]

        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter unique coupon code'
            }),
            'discount_percentage': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'max': '90'
            }),
            'min_order_amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0'
            }),
            'expiry_date': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-input'
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'checkbox-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set input formats for datetime field
        self.fields['expiry_date'].input_formats = ['%Y-%m-%dT%H:%M']

    def clean_discount_percentage(self):
        value = self.cleaned_data['discount_percentage']
        if value <= 0 or value > 90:
            raise forms.ValidationError(
                "Discount must be between 1% and 90%"
            )
        return value