import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "handmade_ceramics.settings")
django.setup()

from user_authentication.models import OTP

otps = OTP.objects.filter(email='nasidox184@dwseal.com').order_by('created_at')
for o in otps:
    print(f"[{o.created_at}] Used? {o.is_used}")
