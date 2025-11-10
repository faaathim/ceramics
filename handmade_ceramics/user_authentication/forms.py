from django import forms
from django.contrib.auth import get_user_model
import re

User = get_user_model()

class SignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(max_length=254, required=True)
    password1 = forms.CharField(
        widget=forms.PasswordInput(),
        label="Password",
        help_text="Minimum 8 chars, at least 1 letter and 1 digit."
    )
    password2 = forms.CharField(widget=forms.PasswordInput(), label="Confirm password")

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_password1(self):
        pw = self.cleaned_data.get('password1')
        if len(pw) < 8:
            raise forms.ValidationError("Password must be at least 8 characters.")
        if not re.search(r'[A-Za-z]', pw) or not re.search(r'\d', pw):
            raise forms.ValidationError("Password must include at least one letter and one digit.")
        return pw

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password1') and cleaned.get('password2'):
            if cleaned['password1'] != cleaned['password2']:
                raise forms.ValidationError("Passwords do not match.")
        return cleaned


class OTPForm(forms.Form):
    code = forms.CharField(max_length=4, min_length=4, required=True, label="4-digit code")

    def clean_code(self):
        code = self.cleaned_data['code'].strip()
        if not code.isdigit():
            raise forms.ValidationError("Code must be numeric.")
        if len(code) != 4:
            raise forms.ValidationError("Code must be 4 digits.")
        return code



class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'}),
        error_messages={'required': 'Email is required'}
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}),
        error_messages={'required': 'Password is required'}
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(),
        label="Remember me"
    )

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'placeholder': 'Enter your registered email',
        'class': 'form-control'
    }))

class VerifyOTPForm(forms.Form):
    otp = forms.CharField(max_length=4, widget=forms.TextInput(attrs={
        'placeholder': 'Enter 4-digit OTP',
        'class': 'form-control',
        'maxlength': '4'
    }))

class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'New Password',
        'class': 'form-control'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Confirm Password',
        'class': 'form-control'
    }))

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password')
        p2 = cleaned_data.get('confirm_password')

        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data