import uuid
from typing import Any

from graphql import GraphQLScalarType, Undefined, ValueNode

from undine.errors import handle_conversion_errors
from undine.utils import TypeDispatcher

__all__ = [
    "GraphQLUUID",
    "parse_uuid",
]


error_wrapper = handle_conversion_errors("UUID")
parse_uuid = TypeDispatcher[Any, uuid.UUID](wrapper=error_wrapper)


@parse_uuid.register
def _(input_value: uuid.UUID) -> Any:
    return input_value


@parse_uuid.register
def _(input_value: str) -> Any:
    return uuid.UUID(hex=input_value)


@parse_uuid.register
def _(input_value: bytes) -> Any:
    try:
        return uuid.UUID(bytes=input_value)  # big endian
    except ValueError:
        return uuid.UUID(bytes_le=input_value)  # little endian


@parse_uuid.register
def _(input_value: int) -> Any:
    return uuid.UUID(int=input_value)


@error_wrapper
def serialize(output_value: Any) -> str:
    return str(parse_uuid(output_value))


@error_wrapper
def parse_literal(value_node: ValueNode, _variables: Any = None) -> Any:
    value: Any = getattr(value_node, "value", Undefined)
    return parse_uuid(value)


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
    parse_literal=parse_literal,
)
