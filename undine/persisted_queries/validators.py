import string

from django.core.exceptions import ValidationError
from graphql import GraphQLError, parse, specified_rules, validate

from undine.settings import undine_settings

__all__ = [
    "validate_document",
    "validate_name",
]


def validate_name(value: str) -> str:
    """Validate the name of a persisted query."""
    if not all(c in string.ascii_letters for c in value):
        msg = "Name must only contain ASCII letters."
        raise ValidationError(msg)
    return value


def validate_document(value: str) -> str:
    """Validate the document of a persisted query."""
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
        rules=(*specified_rules, *undine_settings.ADDITIONAL_VALIDATION_RULES),
        max_errors=undine_settings.MAX_ERRORS,
    )
    if validation_errors:
        raise ValidationError([error.message for error in validation_errors])

    return value
