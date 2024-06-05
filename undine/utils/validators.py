from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, get_available_image_extensions

from undine.utils.text import comma_sep_str

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile


__all__ = [
    "validate_file_upload",
    "validate_file_url",
    "validate_image_url",
    "validate_is_allowed_image_extension",
    "validate_url",
]


url_validator = URLValidator()


def validate_url(url: str) -> str:
    url_validator(url)
    return url


def validate_file_url(url: str) -> str:
    url_validator(url)

    extension = Path(url).suffix[1:]
    if not extension:
        msg = "File URLs must have a file extension."
        raise ValidationError(msg)

    return url


def validate_image_url(url: str) -> str:
    url_validator(url)

    extension = Path(url).suffix[1:]
    if not extension:
        msg = "Image URLs must have a file extension."
        raise ValidationError(msg)

    validate_is_allowed_image_extension(extension)

    return url


def validate_is_allowed_image_extension(extension: str) -> str:
    allowed_extensions = get_available_image_extensions()

    if extension.lower() not in allowed_extensions:
        allowed_str = comma_sep_str(allowed_extensions, last_sep="or", quote=True)
        msg = f"File extension '{extension}' is not allowed. Allowed extensions are: {allowed_str}."
        raise ValidationError(msg)

    return extension


def validate_file_upload(value: UploadedFile) -> UploadedFile:
    if not value.name:
        msg = "No filename could be determined."
        raise ValidationError(msg)

    return value


def validate_image_upload(value: UploadedFile) -> UploadedFile:
    try:
        from PIL import Image  # noqa: PLC0415
    except ImportError as error:  # pragma: no cover
        msg = "The `Pillow` library is not installed. Could not perform image validation."
        raise ValidationError(msg) from error

    if not value.name:
        msg = "No filename could be determined."
        raise ValidationError(msg)

    try:
        name, extension = value.name.rsplit(".", 1)
    except ValueError as error:
        msg = "Filename must have two parts: the name and the extension."
        raise ValidationError(msg) from error

    if not name:
        msg = "Filename must not be empty."
        raise ValidationError(msg)

    if not extension:
        msg = "Filename must have an extension."
        raise ValidationError(msg)

    extension = value.name.split(".")[-1]
    validate_is_allowed_image_extension(extension)

    file = BytesIO(value.read())
    value.seek(0)  # Go back to the beginning of the file after reading it

    try:
        Image.open(file).verify()
    except Exception as error:
        msg = "File either not an image or a corrupted image."
        raise ValidationError(msg) from error

    return value
