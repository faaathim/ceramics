from django.conf import settings
from django.db import models
from django.core.validators import RegexValidator

mobile_validator = RegexValidator(
    regex=r'^\+?\d{7,15}$',
    message='Enter a valid phone number (7-15 digits, optional leading +).'
)

class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    mobile_number = models.CharField(
        max_length=20,
        validators=[mobile_validator],
        blank=True,
        help_text='Include country code if applicable (e.g. +91...).'
    )
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    image = models.ImageField(
        upload_to='profile_images/',
        blank=True,
        null=True,
        default='profile_images/default.png'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile for {self.user}'
