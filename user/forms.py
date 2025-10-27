# accounts/forms.py
from django import forms
from .models import Profile

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'first_name', 
            'last_name', 
            'mobile_number', 
            'address', 
            'city', 
            'state', 
            'image'  # Added profile image field
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        """
        Customize form labels and help texts if needed.
        """
        super().__init__(*args, **kwargs)
        self.fields['image'].label = "Profile Image"
        self.fields['image'].required = False  # Image is optional
        self.fields['image'].widget.attrs.update({'accept': 'image/*'})
