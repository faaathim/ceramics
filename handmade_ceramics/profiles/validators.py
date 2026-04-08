import re
import imghdr
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile


# ✅ MOBILE VALIDATION
def validate_indian_mobile(value):
    if not value or not isinstance(value, str):
        return

    cleaned = re.sub(r'[\s\-]', '', value)
    pattern = r'^(\+91)?[6-9]\d{9}$|^0[6-9]\d{9}$'

    if not re.match(pattern, cleaned):
        raise ValidationError("Enter a valid Indian mobile number.")


# ✅ PINCODE
def validate_indian_pincode(value):
    if not value:
        return

    if not re.match(r'^\d{6}$', value):
        raise ValidationError("Enter a valid 6-digit PIN code.")


# ✅ TEXT
def validate_small_text(value, min_len=2, max_len=100):
    if not value:
        return

    cleaned = value.strip()

    if len(cleaned) < min_len or len(cleaned) > max_len:
        raise ValidationError(
            f"Value must be between {min_len} and {max_len} characters."
        )


def validate_city(value):
    validate_small_text(value, 2, 100)


def validate_state(value):
    validate_small_text(value, 2, 100)


# ✅ NAME
def validate_name(value):
    if not value:
        return value

    cleaned = value.strip()

    if len(cleaned) < 2:
        raise ValidationError("Name must be at least 2 characters long.")

    if not re.match(r'^[A-Za-z\s]+$', cleaned):
        raise ValidationError("Only letters and spaces allowed.")

    return cleaned


# ✅ IMAGE
def validate_profile_image(file_obj):
    if not file_obj:
        return

    if isinstance(file_obj, (UploadedFile, InMemoryUploadedFile)):

        max_size = 2 * 1024 * 1024
        if file_obj.size > max_size:
            raise ValidationError("Image too large (max 2MB).")

        file_obj.seek(0)
        file_type = imghdr.what(file_obj)
        file_obj.seek(0)

        if file_type not in ("jpeg", "png"):
            raise ValidationError("Only JPEG and PNG allowed.")