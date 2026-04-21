import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "handmade_ceramics.settings")
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.filter(email='nasidox184@dwseal.com').delete()
print("Test user deleted.")
