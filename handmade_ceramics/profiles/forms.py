from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import Profile, Address
from .validators import (
    validate_profile_image,
    validate_indian_mobile,
    validate_name
)

User = get_user_model()


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = Profile
        fields = ['profile_image', 'mobile']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.user = user

        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

    def clean_first_name(self):
        return validate_name(self.cleaned_data.get('first_name'))

    def clean_last_name(self):
        return validate_name(self.cleaned_data.get('last_name'))

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        validate_indian_mobile(mobile)
        return mobile

    def clean_profile_image(self):
        image = self.cleaned_data.get('profile_image')
        validate_profile_image(image)
        return image

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if email and User.objects.filter(email__iexact=email).exclude(
            pk=getattr(self.user, 'pk', None)
        ).exists():
            raise forms.ValidationError("This email is already in use.")

        return email

    def save(self, commit=True):
        profile = super().save(commit=False)

        if self.user:
            self.user.first_name = self.cleaned_data.get('first_name')
            self.user.last_name = self.cleaned_data.get('last_name')

        if commit:
            profile.full_clean()
            profile.save()
            if self.user:
                self.user.save()

        return profile


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'first_name', 'last_name', 'country', 'street_address',
            'city', 'state', 'pin_code', 'phone'
        ]
        widgets = {
            'street_address': forms.Textarea(attrs={'rows': 2}),
        }


class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput)
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        if not self.user.check_password(self.cleaned_data.get("current_password")):
            raise forms.ValidationError("Incorrect current password.")
        return self.cleaned_data.get("current_password")

    def clean(self):
        cleaned = super().clean()
        new = cleaned.get("new_password")
        confirm = cleaned.get("confirm_password")

        if new != confirm:
            raise forms.ValidationError("Passwords do not match.")

        if new:
            validate_password(new, self.user)

        return cleaned