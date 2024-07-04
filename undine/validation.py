from __future__ import annotations

from functools import wraps
from pathlib import Path
from typing import Callable, ParamSpec, TypeVar

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, get_available_image_extensions

from undine.utils import comma_sep_str

P = ParamSpec("P")
T = TypeVar("T")


def _capture_validation_errors(func: Callable[P, T]) -> Callable[P, T]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except ValidationError as error:
            if error.params is not None:
                error.message %= error.params
            raise ValueError(error.message) from error

    return wrapper


url_validator = URLValidator()


@_capture_validation_errors
def validate_url(url: str) -> str:
    url_validator(url)
    return url


@_capture_validation_errors
def validate_file_url(url: str) -> str:
    url_validator(url)
    extension = Path(url).suffix[1:].lower()
    if not extension:
        msg = "File URLs must have a file extension."
        raise ValidationError(msg)
    return url


@_capture_validation_errors
def validate_image_url(url: str) -> str:
    url_validator(url)
    validate_extensions(url, allowed_extensions=get_available_image_extensions())
    return url


def validate_extensions(string: str, allowed_extensions: list[str]) -> str:
    extension = Path(string).suffix[1:].lower()
    if extension not in allowed_extensions:
        msg = (
            f"File extension '{extension}' is not allowed. "
            f"Allowed extensions are: {comma_sep_str(allowed_extensions, last_sep='or', quote=True)}."
        )
        raise ValidationError(msg)
    return string
