from typing import Any, NoReturn

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from graphql import GraphQLScalarType

from undine.errors.error_handlers import handle_conversion_errors
from undine.utils.dispatcher import FunctionDispatcher
from undine.utils.text import dotpath

__all__ = [
    "GraphQLEmail",
    "parse_email",
]


error_wrapper = handle_conversion_errors("Email")
parse_email = FunctionDispatcher[Any, str](wrapper=error_wrapper)


@parse_email.register
def _(input_value: Any) -> NoReturn:
    msg = f"Type '{dotpath(type(input_value))}' is not supported"
    raise ValueError(msg)


@parse_email.register
def _(input_value: str) -> str:
    try:
        validate_email(input_value)
    except ValidationError as error:
        raise ValueError(error.message) from error
    return input_value


@error_wrapper
def serialize(output_value: Any) -> str:
    return parse_email(output_value)


GraphQLEmail = GraphQLScalarType(
    name="Email",
    description="The `Email` scalar type represents a valid email address.",
    serialize=serialize,
    parse_value=parse_email,
)
