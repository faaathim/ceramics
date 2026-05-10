# utils.py
from django.core.exceptions import ValidationError


def validate_variant_images(images):
    total = len(images)

    if total < 3:
        raise ValidationError(
            "Minimum 3 images are required."
        )

    if total > 7:
        raise ValidationError(
            "Maximum 7 images are allowed."
        )

    valid_extensions = ['jpg', 'jpeg', 'png', 'webp']

    for image in images:

        if image.size > 5 * 1024 * 1024:
            raise ValidationError(
                f"{image.name} exceeds 5MB limit."
            )

        ext = image.name.split('.')[-1].lower()

        if ext not in valid_extensions:
            raise ValidationError(
                f"{image.name} has unsupported format."
            )# utils.py
from django.core.exceptions import ValidationError


def validate_variant_images(images):
    total = len(images)

    if total < 3:
        raise ValidationError(
            "Minimum 3 images are required."
        )

    if total > 7:
        raise ValidationError(
            "Maximum 7 images are allowed."
        )

    valid_extensions = ['jpg', 'jpeg', 'png', 'webp']

    for image in images:

        if image.size > 5 * 1024 * 1024:
            raise ValidationError(
                f"{image.name} exceeds 5MB limit."
            )

        ext = image.name.split('.')[-1].lower()

        if ext not in valid_extensions:
            raise ValidationError(
                f"{image.name} has unsupported format."
            )