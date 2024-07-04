import uuid
from typing import Any, NoReturn

from graphql import GraphQLScalarType

from undine.errors import handle_conversion_errors
from undine.utils import TypeDispatcher, dotpath

__all__ = [
    "GraphQLUUID",
    "parse_uuid",
]


error_wrapper = handle_conversion_errors("UUID")
parse_uuid = TypeDispatcher[Any, uuid.UUID](wrapper=error_wrapper)


@parse_uuid.register
def _(input_value: Any) -> NoReturn:
    msg = f"Type '{dotpath(type(input_value))}' is not supported"
    raise ValueError(msg)


@parse_uuid.register
def _(input_value: uuid.UUID) -> Any:
    return input_value


@parse_uuid.register
def _(input_value: str) -> Any:
    return uuid.UUID(hex=input_value)


@parse_uuid.register
def _(input_value: bytes) -> Any:
    return uuid.UUID(bytes=input_value)


@parse_uuid.register
def _(input_value: int) -> Any:
    return uuid.UUID(int=input_value)


@error_wrapper
def serialize(output_value: Any) -> str:
    return str(parse_uuid(output_value))


GraphQLUUID = GraphQLScalarType(
    name="UUID",
    description=(
        "The `UUID` scalar type represents any "
        "[UUID](https://en.wikipedia.org/wiki/Universally_unique_identifier) value "
        "as defined by [RFC 4122](https://tools.ietf.org/html/rfc4122). "
        "Maps to Python's `uuid.UUID` type."
    ),
    serialize=serialize,
    parse_value=parse_uuid,
)
