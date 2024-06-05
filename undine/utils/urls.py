from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, get_available_image_extensions

from undine.errors.error_handlers import handle_validation_errors
from undine.utils.text import comma_sep_str

if TYPE_CHECKING:
    from collections.abc import Sequence

url_validator = URLValidator()


@handle_validation_errors
def validate_url(url: str) -> str:
    url_validator(url)
    return url


@handle_validation_errors
def validate_file_url(url: str) -> str:
    url_validator(url)
    extension = Path(url).suffix[1:].lower()
    if not extension:
        msg = "File URLs must have a file extension."
        raise ValidationError(msg)
    return url


@handle_validation_errors
def validate_image_url(url: str) -> str:
    url_validator(url)
    validate_extensions(url, allowed_extensions=get_available_image_extensions())
    return url


@handle_validation_errors
def validate_extensions(string: str, allowed_extensions: Sequence[str]) -> str:
    extension = Path(string).suffix[1:].lower()
    if extension not in allowed_extensions:
        msg = (
            f"File extension '{extension}' is not allowed. "
            f"Allowed extensions are: {comma_sep_str(allowed_extensions, last_sep='or', quote=True)}."
        )
        raise ValidationError(msg)
    return string
