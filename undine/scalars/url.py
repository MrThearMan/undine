from typing import Any

from django.core.validators import URLValidator
from graphql import GraphQLScalarType, Undefined, ValueNode

from undine.errors import handle_conversion_errors
from undine.utils import TypeMapper

__all__ = [
    "GraphQLURL",
    "parse_url",
]


error_wrapper = handle_conversion_errors("URL")
parse_url = TypeMapper[Any, str](wrapper=error_wrapper)
validator = URLValidator()


@parse_url.register
def _(input_value: str) -> str:
    validator(input_value)
    return input_value


@error_wrapper
def serialize(output_value: Any) -> str:
    return parse_url(output_value)


@error_wrapper
def parse_literal(value_node: ValueNode, _variables: Any = None) -> str:
    value: Any = getattr(value_node, "value", Undefined)
    return parse_url(value)


GraphQLURL = GraphQLScalarType(
    name="URL",
    description="The `URL` scalar type represents a valid URL.",
    serialize=serialize,
    parse_value=parse_url,
    parse_literal=parse_literal,
)
