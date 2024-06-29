from typing import Any

from django.core.validators import validate_email
from graphql import GraphQLScalarType, Undefined, ValueNode

from undine.errors import handle_conversion_errors
from undine.utils import TypeDispatcher

__all__ = [
    "GraphQLEmail",
    "parse_email",
]


error_wrapper = handle_conversion_errors("Email")
parse_email = TypeDispatcher[Any, str](wrapper=error_wrapper)


@parse_email.register
def _(input_value: str) -> str:
    validate_email(input_value)
    return input_value


@error_wrapper
def serialize(output_value: Any) -> str:
    return parse_email(output_value)


@error_wrapper
def parse_literal(value_node: ValueNode, _variables: Any = None) -> str:
    value: Any = getattr(value_node, "value", Undefined)
    return parse_email(value)


GraphQLEmail = GraphQLScalarType(
    name="Email",
    description="The `Email` scalar type represents a valid email address.",
    serialize=serialize,
    parse_value=parse_email,
    parse_literal=parse_literal,
)
