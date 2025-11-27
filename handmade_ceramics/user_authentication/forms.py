from django import forms
import re

# Signup form for new user registration
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
        from django.contrib.auth import get_user_model
        User = get_user_model()
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_password1(self):
        pw = self.cleaned_data.get('password1') or ""
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


# Generic 4-digit OTP form (used for signup verification)
class OTPForm(forms.Form):
    code = forms.CharField(
        max_length=4,
        min_length=4,
        required=True,
        label="4-digit code",
        widget=forms.TextInput(attrs={'placeholder': '1234'})
    )

    def clean_code(self):
        code = self.cleaned_data['code'].strip()
        if not code.isdigit() or len(code) != 4:
            raise forms.ValidationError("Enter a 4-digit numeric code.")
        return code


# Login form
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


# Forgot password (enter email)
class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'placeholder': 'Enter your registered email',
        'class': 'form-control'
    }))


# Reuse OTPForm for reset verification UI (template otp_forgot.html)
class VerifyOTPForm(OTPForm):
    pass


# Reset password form
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
        # Optionally validate complexity here (reuse same rules as signup if desired)
        if p1 and (len(p1) < 8 or not re.search(r'[A-Za-z]', p1) or not re.search(r'\d', p1)):
            raise forms.ValidationError("Password must be at least 8 chars and include a letter and a digit.")
        return cleaned_data
