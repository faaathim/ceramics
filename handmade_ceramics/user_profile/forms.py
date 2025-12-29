# user_profile/forms.py
from django import forms
from django.contrib.auth import get_user_model
from .models import Profile
from .validators import validate_profile_image, validate_indian_mobile, validate_small_text

User = get_user_model()

class ProfileForm(forms.ModelForm):
    # We keep user-related fields on the form so we can edit User first_name/last_name/email together
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = Profile
        fields = ['profile_image', 'mobile']

    def __init__(self, *args, **kwargs):
        # accept the currently logged-in user so we can check uniqueness for email, etc.
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.user = user

        # initialize user fields if we have the user
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        # use the validator function directly to reuse same logic
        validate_indian_mobile(mobile)
        return mobile

    def clean_profile_image(self):
        image = self.cleaned_data.get('profile_image')
        validate_profile_image(image)
        return image

    def clean_email(self):
        # make sure the new email isn't already taken by another user
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exclude(pk=getattr(self.user, 'pk', None)).exists():
            raise forms.ValidationError("This email is already in use by another account.")
        return email

    def save(self, commit=True):
        # Save profile and also update the built-in User model fields (first_name, last_name, email)
        profile = super().save(commit=False)

        # update user fields
        if self.user:
            self.user.first_name = self.cleaned_data.get('first_name', self.user.first_name)
            self.user.last_name = self.cleaned_data.get('last_name', self.user.last_name)

            # email is handled in view via OTP flow; we still set it if unchanged
            new_email = self.cleaned_data.get('email')
            if new_email and new_email == self.user.email:
                self.user.email = new_email

        if commit:
            # full_clean on profile ensures model validators run
            profile.full_clean()
            profile.save()
            if self.user:
                self.user.save()
        return profile
