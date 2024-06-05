from __future__ import annotations

import string
from typing import Any

from django.core.exceptions import ValidationError
from graphql import GraphQLError, parse, validate

from undine.settings import undine_settings
from undine.utils.graphql.validation_rules import get_validation_rules

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

    validation_errors = validate(
        schema=undine_settings.SCHEMA,
        document_ast=document,
        rules=get_validation_rules(),
        max_errors=undine_settings.MAX_ERRORS,
    )
    if validation_errors:
        raise ValidationError([error.message for error in validation_errors])
