from django.db import models
from django.conf import settings
from django.utils import timezone
import random
from django.contrib.auth.models import User
from datetime import timedelta

User = settings.AUTH_USER_MODEL

class OTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=4)           
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveSmallIntegerField(default=0)  
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP {self.code} for {self.user}"

    @classmethod
    def generate_otp(cls, user):
        code = f"{random.randint(0, 9999):04d}"  
        otp = cls.objects.create(user=user, code=code)
        return otp


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.created_at + timedelta(minutes=5)

    def __str__(self):
        return f"{self.user.username} - {self.otp}"