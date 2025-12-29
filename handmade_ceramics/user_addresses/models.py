from django.db import models
from django.contrib.auth import get_user_model

# IMPORT YOUR VALIDATORS  
from user_profile.validators import (
    validate_city,
    validate_state,
    validate_indian_mobile,
    validate_indian_pincode
)

User = get_user_model()


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)

    country = models.CharField(max_length=100)

    street_address = models.CharField(max_length=255)

    # APPLY VALIDATORS HERE
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
