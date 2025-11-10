# user_profile/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
import random
from datetime import timedelta

User = settings.AUTH_USER_MODEL


def profile_image_upload_path(instance, filename):
    return f'profiles/{instance.user.id}/{filename}'


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_image = models.ImageField(upload_to=profile_image_upload_path, blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True)
    primary_address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


class EmailChangeOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    new_email = models.EmailField()
    otp = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} - {self.new_email}"

    def is_valid(self):
        return not self.is_used and timezone.now() < self.created_at + timedelta(minutes=5)

    @classmethod
    def generate_otp(cls, user, new_email):
        code = f"{random.randint(0, 9999):04d}"
        cls.objects.create(user=user, new_email=new_email, otp=code)
        return code
