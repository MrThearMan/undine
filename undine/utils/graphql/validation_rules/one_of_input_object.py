from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING, Any

from graphql import (
    GraphQLError,
    GraphQLInputObjectType,
    NonNullTypeNode,
    NullValueNode,
    ValidationRule,
    VariableNode,
    get_named_type,
)

if TYPE_CHECKING:
    from graphql import GraphQLNamedType, ObjectValueNode, ValidationContext, VariableDefinitionNode, VisitorAction


__all__ = [
    "OneOfInputObjectTypeRule",
    "core_implements_one_of_directive",
    "get_one_of_input_object_type_extension",
    "is_one_of_input_object",
    "validate_one_of_input_object_variable_value",
]


class OneOfInputObjectTypeRule(ValidationRule):
    """
    Forwards `@oneOf` directive validation from GraphQL core `v3.3.0a8`

    See: graphql/validation/rules/values_of_correct_type.py
    """

    def __init__(self, context: ValidationContext) -> None:
        super().__init__(context)
        self.variable_definitions: dict[str, VariableDefinitionNode] = {}

    def enter_operation_definition(self, *_args: Any) -> None:
        self.variable_definitions.clear()

    def enter_variable_definition(self, definition: VariableDefinitionNode, *_args: Any) -> None:
        self.variable_definitions[definition.variable.name.value] = definition

    def enter_object_value(self, node: ObjectValueNode, *_args: Any) -> VisitorAction:
        named_type: GraphQLNamedType | None = get_named_type(self.context.get_input_type())
        if named_type is None or not isinstance(named_type, GraphQLInputObjectType):
            return None

        if not is_one_of_input_object(named_type):
            return None

        typename = named_type.name

        if len(node.fields) != 1:
            msg = f"OneOf Input Object '{typename}' must specify exactly one key."
            self.context.report_error(GraphQLError(msg, node))
            return None

        key = node.fields[0].name.value
        value = node.fields[0].value

        if isinstance(value, NullValueNode):
            msg = f"Field '{typename}.{key}' must be non-null."
            self.context.report_error(GraphQLError(msg, node))
            return None

        if isinstance(value, VariableNode):
            variable_name = value.name.value
            definition = self.variable_definitions[variable_name]

            if not isinstance(definition.type, NonNullTypeNode):
                msg = f"Variable '{variable_name}' must be non-nullable to be used for OneOf Input Object '{typename}'."
                self.context.report_error(GraphQLError(msg, node))

        return None


@cache
def core_implements_one_of_directive() -> bool:
    from graphql.type import directives  # noqa: PLC0415

    return "GraphQLOneOfDirective" in dir(directives)


def validate_one_of_input_object_variable_value(value: dict[str, Any], *, typename: str) -> dict[str, Any]:
    if core_implements_one_of_directive():
        return value

    if len(value) != 1:
        msg = f"OneOf Input Object '{typename}' must specify exactly one key."
        raise GraphQLError(msg)

    field_key, field_value = next(iter(value.items()))

    if field_value is None:
        msg = f"Field '{typename}.{field_key}' must be non-null."
        raise GraphQLError(msg)

    return value


def is_one_of_input_object(input_object_type: GraphQLInputObjectType) -> bool:
    return input_object_type.extensions.get("_undine_is_one_of", False)


def get_one_of_input_object_type_extension() -> dict[str, Any]:
    return {"_undine_is_one_of": True}
