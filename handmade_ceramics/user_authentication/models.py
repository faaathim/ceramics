from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import random

User = settings.AUTH_USER_MODEL

class OTP(models.Model):
    PURPOSE_CHOICES = (
        ('signup', 'Signup'),
        ('reset', 'Password Reset'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=4)
    purpose = models.CharField(max_length=10, choices=PURPOSE_CHOICES, default="signup")
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)  # Added attempt tracking
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def generate_otp():
        return str(random.randint(1000, 9999))

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)  # Extended expiry

    def __str__(self):
        return f"{self.user} - {self.purpose}"
