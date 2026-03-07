# user_profile/validators.py

import imghdr
import re
from django.core.exceptions import ValidationError
import imghdr
from django.core.files.uploadedfile import UploadedFile
from cloudinary.models import CloudinaryResource

def validate_indian_mobile(value):
    if not value or not isinstance(value, str):
        return

    cleaned = re.sub(r'[\s\-]', '', value)
    pattern = r'^(\+91)?[6-9]\d{9}$|^0[6-9]\d{9}$'
    if not re.match(pattern, cleaned):
        raise ValidationError("Enter a valid Indian mobile number.")


def validate_indian_pincode(value):
    """
    Validates if value is exactly a 6-digit Indian PIN code.
    """
    if not value:
        return
    
    print("inside validate")

    if not re.match(r'^\d{6}$', value):
        raise ValidationError("Enter a valid 6-digit PIN code (e.g. 560001).")

def validate_small_text(value, min_len=2, max_len=100):
    """
    A helper function that checks text length.
    Not used directly in models, but wrapped by other validators.
    """
    if not value:
        return

    cleaned = value.strip()

    if len(cleaned) < min_len or len(cleaned) > max_len:
        raise ValidationError(
            f"Value must be between {min_len} and {max_len} characters."
        )


# -----------------------------------------------------
# 4. VALIDATORS WRAPPING THE GENERIC TEXT CHECK
# -----------------------------------------------------
def validate_city(value):
    """
    City name must be 2 to 100 characters.
    """
    validate_small_text(value, 2, 100)


def validate_state(value):
    """
    State name must be 2 to 100 characters.
    """
    validate_small_text(value, 2, 100)


# -----------------------------------------------------
# 5. VALIDATE PROFILE IMAGE (JPEG/PNG + <= 2MB)
# -----------------------------------------------------
def validate_profile_image(file_obj):
    if not file_obj:
        return

    from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile
    import imghdr

    # Check file size if freshly uploaded
    if isinstance(file_obj, (UploadedFile, InMemoryUploadedFile)):
        max_size = 2 * 1024 * 1024  # 2 MB
        if file_obj.size > max_size:
            raise ValidationError("Image too large. Maximum allowed size is 2 MB.")

        # Check file type safely
        file_obj.seek(0)
        file_type = imghdr.what(file_obj)
        file_obj.seek(0)
        if file_type not in ("jpeg", "png"):
            raise ValidationError("Invalid image format. Only JPEG and PNG are allowed.")
