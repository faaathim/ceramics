from django.db import models
from django.utils import timezone
from datetime import timedelta
import random
from django.contrib.auth import get_user_model
from cloudinary.models import CloudinaryField

from .validators import (
    validate_profile_image,
    validate_indian_mobile,
    validate_indian_pincode,
    validate_city,
    validate_state,
)

User = get_user_model()


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    profile_image = CloudinaryField('profile_image', blank=True, null=True)

    mobile = models.CharField(
        max_length=20,
        blank=True,
        validators=[validate_indian_mobile]
    )

    def __str__(self):
        return f"Profile of {self.user.username}"

    def clean(self):
        validate_profile_image(self.profile_image)


class EmailChangeOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    new_email = models.EmailField()
    otp = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} - {self.new_email}"

    def is_valid(self):
        return (
            not self.is_used
            and timezone.now() < self.created_at + timedelta(minutes=5)
        )

    @classmethod
    def generate_otp(cls, user, new_email):
        code = f"{random.randint(0, 9999):04d}"
        obj = cls.objects.create(
            user=user,
            new_email=new_email,
            otp=code
        )
        return obj.otp


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)

    country = models.CharField(max_length=100)
    street_address = models.CharField(max_length=255)

    city = models.CharField(max_length=100, validators=[validate_city])
    state = models.CharField(max_length=100, validators=[validate_state])
    pin_code = models.CharField(max_length=20, validators=[validate_indian_pincode])
    phone = models.CharField(max_length=20, validators=[validate_indian_mobile])

    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.city}"