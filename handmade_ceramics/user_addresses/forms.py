from django import forms
from .models import Address

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'first_name', 'last_name', 'country', 'street_address',
            'city', 'state', 'pin_code', 'phone', 'email'
        ]
        widgets = {
            'street_address': forms.Textarea(attrs={'rows': 2}),
        }
