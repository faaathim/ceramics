from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('username', 'email', 'is_staff', 'is_blocked', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_blocked')
    search_fields = ('username', 'email')
    ordering = ('-date_joined',)

    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('is_blocked', 'otp')}),
    )
