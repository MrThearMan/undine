from typing import Any

from graphql import (
    BooleanValueNode,
    FloatValueNode,
    GraphQLScalarType,
    IntValueNode,
    ListValueNode,
    ObjectValueNode,
    StringValueNode,
    ValueNode,
)

from undine.errors import handle_conversion_errors
from undine.utils import TypeMapper

__all__ = [
    "GraphQLAny",
    "parse_generic",
]


error_wrapper = handle_conversion_errors("Generic")
parse_generic: TypeMapper[Any, Any]
parse_generic = TypeMapper("parse_generic", wrapper=error_wrapper)


@parse_generic.register
def _(input_value: object) -> Any:
    return input_value


@parse_generic.register
def _(input_value: type) -> Any:
    return input_value


@error_wrapper
def serialize(output_value: Any) -> str:
    return str(output_value)


@error_wrapper
def parse_literal(value_node: ValueNode, _variables: Any = None) -> Any:
    if isinstance(value_node, (StringValueNode, BooleanValueNode)):
        return value_node.value

    if isinstance(value_node, IntValueNode):
        return int(value_node.value)

    if isinstance(value_node, FloatValueNode):
        return float(value_node.value)

    if isinstance(value_node, ListValueNode):
        return [parse_literal(value) for value in value_node.values]

    if isinstance(value_node, ObjectValueNode):
        return {field.name.value: parse_literal(field.value) for field in value_node.fields}

    return None


GraphQLAny = GraphQLScalarType(
    name="Any",
    description="The `Any` scalar type can be anything. It is used e.g. for type unions.",
    serialize=serialize,
    parse_value=parse_generic,
    parse_literal=parse_literal,
)
