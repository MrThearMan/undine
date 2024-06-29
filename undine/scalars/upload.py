from typing import Any

from graphql import GraphQLScalarType, ValueNode

from undine.errors import handle_conversion_errors
from undine.utils import TypeDispatcher

__all__ = [
    "GraphQLUpload",
    "parse_upload",
]


error_wrapper = handle_conversion_errors("Upload")
parse_upload = TypeDispatcher[Any, Any](wrapper=error_wrapper)


@parse_upload.register
def _(input_value: Any) -> Any:
    return input_value


@error_wrapper
def serialize(output_value: Any) -> str:
    return str(output_value)


@error_wrapper
def parse_literal(value_node: ValueNode, _variables: Any = None) -> Any:
    return value_node


GraphQLUpload = GraphQLScalarType(
    name="Upload",
    description="Represents a file upload.",
    serialize=serialize,
    parse_value=parse_upload,
    parse_literal=parse_literal,
)
