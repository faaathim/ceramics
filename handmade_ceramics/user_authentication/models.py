# user_authentication/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import random
import hashlib

User = settings.AUTH_USER_MODEL

class OTP(models.Model):
    PURPOSE_CHOICES = (
        ('signup', 'Signup'),
        ('reset', 'Password Reset'),
    )

    MAX_ATTEMPTS = 5

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField()
    code_hash = models.CharField(max_length=64)
    purpose = models.CharField(max_length=10, choices=PURPOSE_CHOICES)
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def generate_otp():
        return str(random.randint(100000, 999999))

    @staticmethod
    def hash_otp(code):
        return hashlib.sha256(code.encode()).hexdigest()

    def verify(self, code):
        if self.attempts >= self.MAX_ATTEMPTS:
            return False
        return self.code_hash == self.hash_otp(code)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=3)