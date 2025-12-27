from __future__ import annotations

import string
from typing import Any

from django.core.exceptions import ValidationError
from graphql import GraphQLError, parse

from undine.execution import _validate
from undine.settings import undine_settings

__all__ = [
    "validate_document",
    "validate_document_id",
]


VALID_CHARS = frozenset(string.ascii_letters + string.digits + ":-._~")


def validate_document_id(value: Any) -> None:
    """Validate the document id of a persisted document."""
    if not isinstance(value, str):
        msg = "Document ID must be a string"
        raise ValidationError(msg)

    invalid_chars: set[str] = {c for c in value if c not in VALID_CHARS}
    if invalid_chars:
        msg = f"Document ID contains invalid characters: {' '.join(sorted(invalid_chars))}"
        raise ValidationError(msg)


def validate_document(value: Any) -> None:
    """Validate the document of a persisted document."""
    if not isinstance(value, str):
        msg = "Document must be a string"
        raise ValidationError(msg)

    try:
        document = parse(
            source=value,
            no_location=undine_settings.NO_ERROR_LOCATION,
            max_tokens=undine_settings.MAX_TOKENS,
        )
    except GraphQLError as parse_error:
        raise ValidationError(parse_error.message) from parse_error

    validation_errors = _validate(document=document)
    if validation_errors:
        raise ValidationError([error.message for error in validation_errors])
