import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "handmade_ceramics.settings")
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

user = User.objects.filter(email='nasidox184@dwseal.com').first()
if user:
    print(f"User found: {user.email}")
    print(f"Date joined: {user.date_joined}")
    print(f"Is active: {user.is_active}")
else:
    print("User not found.")
