from typing import Any, NoReturn

from graphql import GraphQLScalarType

from undine.errors.error_handlers import handle_conversion_errors
from undine.utils.dispatcher import FunctionDispatcher
from undine.utils.text import dotpath
from undine.utils.urls import validate_url

__all__ = [
    "GraphQLURL",
    "parse_url",
]


error_wrapper = handle_conversion_errors("URL")
parse_url = FunctionDispatcher[Any, str](wrapper=error_wrapper)


@parse_url.register
def _(input_value: Any) -> NoReturn:
    msg = f"Type '{dotpath(type(input_value))}' is not supported"
    raise ValueError(msg)


@parse_url.register
def _(input_value: str) -> str:
    return validate_url(input_value)


@error_wrapper
def serialize(output_value: Any) -> str:
    return parse_url(output_value)


GraphQLURL = GraphQLScalarType(
    name="URL",
    description="The `URL` scalar type represents a valid URL.",
    serialize=serialize,
    parse_value=parse_url,
)
