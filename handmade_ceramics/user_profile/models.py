# user_profile/models.py

from django.db import models
from django.utils import timezone
from datetime import timedelta
import random
from django.contrib.auth import get_user_model

from .validators import (
    validate_profile_image,
    validate_indian_mobile,
    validate_indian_pincode,
    validate_city,
    validate_state,
)

# Get the active User model
User = get_user_model()


# Upload path for profile images
def profile_image_upload_path(instance, filename):
    """
    Store images under profiles/<user_id>/<filename>
    """
    return f'profiles/{instance.user.id}/{filename}'


class Profile(models.Model):
    """
    Stores additional profile information about a user.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    profile_image = models.ImageField(
        upload_to=profile_image_upload_path,
        blank=True,
        null=True
    )

    mobile = models.CharField(
        max_length=20,
        blank=True,
        validators=[validate_indian_mobile]
    )

    primary_address = models.TextField(blank=True)

    city = models.CharField(
        max_length=100,
        blank=True,
        validators=[validate_city]
    )

    state = models.CharField(
        max_length=100,
        blank=True,
        validators=[validate_state]
    )

    pincode = models.CharField(
        max_length=6,
        blank=True,
        validators=[validate_indian_pincode]
    )

    def __str__(self):
        return f"Profile of {self.user.username}"

    def clean(self):
        """
        Model-level validation for image.
        """
        validate_profile_image(self.profile_image)


class EmailChangeOTP(models.Model):
    """
    Stores OTPs used for email change verification.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    new_email = models.EmailField()
    otp = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} - {self.new_email}"

    def is_valid(self):
        """
        OTP is valid for 5 minutes and only if unused.
        """
        return (
            not self.is_used
            and timezone.now() < self.created_at + timedelta(minutes=5)
        )

    @classmethod
    def generate_otp(cls, user, new_email):
        """
        Generate a 4-digit OTP and store it.
        """
        code = f"{random.randint(0, 9999):04d}"
        obj = cls.objects.create(
            user=user,
            new_email=new_email,
            otp=code
        )
        return obj.otp
