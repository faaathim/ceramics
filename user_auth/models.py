from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    is_blocked = models.BooleanField(default=True)
    otp = models.CharField(max_length=4, blank=True, null=True)
    email=models.EmailField(unique=True)

    def __str__(self):
        return self.username