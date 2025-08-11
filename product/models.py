from django.db import models
from category.models import Category
from django.db.models import Q
from django.db.models.functions import Lower

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/')
    is_listed = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower('name'),
                condition=Q(is_deleted=False),
                name='unique_lowercase_name_not_deleted'
            )
        ]

    def __str__(self):
        return self.name