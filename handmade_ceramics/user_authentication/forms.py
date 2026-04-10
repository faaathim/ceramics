from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
import re

User = get_user_model()


class SignupForm(forms.Form):
    first_name = forms.CharField(max_length=50)
    last_name  = forms.CharField(max_length=50, required=False)
    email      = forms.EmailField()
    password1  = forms.CharField(widget=forms.PasswordInput)
    password2  = forms.CharField(widget=forms.PasswordInput)

    def clean_first_name(self):
        name = self.cleaned_data['first_name'].strip()
        if not re.match(r'^[A-Za-z ]+$', name):
            raise forms.ValidationError("First name should contain only letters.")
        return name

    def clean_last_name(self):
        name = self.cleaned_data.get('last_name', '').strip()
        if name and not re.match(r'^[A-Za-z ]+$', name):
            raise forms.ValidationError("Last name should contain only letters.")
        return name

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        data = super().clean()
        p1, p2 = data.get('password1'), data.get('password2')

        if p1 and p2:
            if p1 != p2:
                raise forms.ValidationError("Passwords do not match.")

            validate_password(p1)

            if len(p1) < 8:
                raise forms.ValidationError("Password must be at least 8 characters.")

        return data


class OTPForm(forms.Form):
    code = forms.CharField(max_length=6, min_length=6)

    def clean_code(self):
        code = self.cleaned_data['code'].strip()
        if not code.isdigit():
            raise forms.ValidationError("OTP must contain digits only.")
        return code


class LoginForm(forms.Form):
    email    = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean_email(self):
        return self.cleaned_data['email'].lower().strip()


class ResetPasswordForm(forms.Form):
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        data = super().clean()
        p1, p2 = data.get('password1'), data.get('password2')

        if p1 and p2:
            if p1 != p2:
                raise forms.ValidationError("Passwords do not match.")

            validate_password(p1)

            if len(p1) < 8:
                raise forms.ValidationError("Password must be at least 8 characters.")

        return data