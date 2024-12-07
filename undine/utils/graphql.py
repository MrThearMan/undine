from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from graphql import (
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLError,
    GraphQLField,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLNullableType,
    GraphQLObjectType,
)

from undine.errors.exceptions import GraphQLCantCreateEnumError, GraphQLDuplicateTypeError
from undine.registies import GRAPHQL_TYPE_REGISTRY

if TYPE_CHECKING:
    from collections.abc import Collection

    from undine.typing import GQLInfo, TGraphQLType
    from undine.utils.reflection import FunctionEqualityWrapper


__all__ = [
    "add_default_status_codes",
    "get_or_create_graphql_enum",
    "get_or_create_input_object_type",
    "get_or_create_interface_type",
    "get_or_create_object_type",
    "maybe_list_or_non_null",
]


def maybe_list_or_non_null(graphql_type: TGraphQLType, *, many: bool, required: bool) -> TGraphQLType:
    """Wrap the given GraphQL type as a list of non-null items and/or non-null if needed."""
    if many is True and not isinstance(graphql_type, GraphQLList):
        if not isinstance(graphql_type, GraphQLNonNull):
            graphql_type = GraphQLNonNull(graphql_type)
        graphql_type = GraphQLList(graphql_type)
    if required is True and not isinstance(graphql_type, GraphQLNonNull):
        graphql_type = GraphQLNonNull(graphql_type)
    return graphql_type


def add_default_status_codes(errors: list[GraphQLError]) -> list[GraphQLError]:
    for error in errors:
        error.extensions.setdefault("status_code", 400)
    return errors


def compare_graphql_types(*, new_type: GraphQLNullableType, existing_type: GraphQLNullableType) -> None:
    """Raises a 'GraphQLDuplicateTypeError' if the existing type is different from the new type."""
    if (
        isinstance(new_type, GraphQLEnumType)
        and isinstance(existing_type, GraphQLEnumType)
        and new_type.values == existing_type.values
    ):
        return

    if (
        isinstance(new_type, GraphQLObjectType)
        and isinstance(existing_type, GraphQLObjectType)
        and new_type._fields == existing_type._fields
    ):
        return

    if (
        isinstance(new_type, GraphQLInputObjectType)
        and isinstance(existing_type, GraphQLInputObjectType)
        and new_type._fields == existing_type._fields
    ):
        return

    raise GraphQLDuplicateTypeError(
        name=new_type.name,
        type_new=type(new_type),
        type_existing=type(existing_type),
    )


def get_or_create_graphql_enum(
    *,
    name: str,
    values: dict[str, str | GraphQLEnumValue],
    description: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> GraphQLEnumType:
    """
    If a GraphQL Type with the same name already exists,
    check if is a GraphQLEnumType and if the its values are the same.
    If they are, return the existing 'GraphQLEnumType'. If not, raise an error.
    Otherwise, create a new 'GraphQLEnumType'.
    """
    for key, value in values.items():
        if isinstance(value, str):
            values[key] = GraphQLEnumValue(value=key, description=value)

    if not values:
        raise GraphQLCantCreateEnumError(name=name)

    enum = GraphQLEnumType(
        name=name,
        values=values,
        description=description,
        extensions=extensions,
    )

    if name in GRAPHQL_TYPE_REGISTRY:
        compare_graphql_types(new_type=enum, existing_type=GRAPHQL_TYPE_REGISTRY[name])
        return GRAPHQL_TYPE_REGISTRY[name]

    GRAPHQL_TYPE_REGISTRY[name] = enum
    return enum


def get_or_create_object_type(
    *,
    name: str,
    fields: dict[str, GraphQLField] | FunctionEqualityWrapper[dict[str, GraphQLField]],
    interfaces: Collection[GraphQLInterfaceType] | None = None,
    description: str | None = None,
    is_type_of: Callable[[Any, GQLInfo], bool] | None = None,
    extensions: dict[str, Any] | None = None,
) -> GraphQLObjectType:
    """
    If a GraphQL Type with the same name already exists,
    check if it is a GraphQLObjectType and its fields are the same.
    If they are, return the existing 'GraphQLObjectType'. If not, raise an error.
    Otherwise, create a new 'GraphQLObjectType'.
    """
    object_type = GraphQLObjectType(
        name=name,
        fields=fields,
        interfaces=interfaces,
        description=description,
        is_type_of=is_type_of,
        extensions=extensions,
    )

    if name in GRAPHQL_TYPE_REGISTRY:
        compare_graphql_types(new_type=object_type, existing_type=GRAPHQL_TYPE_REGISTRY[name])
        return GRAPHQL_TYPE_REGISTRY[name]

    GRAPHQL_TYPE_REGISTRY[name] = object_type
    return object_type


def get_or_create_input_object_type(
    *,
    name: str,
    fields: dict[str, GraphQLInputField] | FunctionEqualityWrapper[dict[str, GraphQLInputField]],
    description: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> GraphQLInputObjectType:
    """
    If a GraphQL Type with the same name already exists,
    check if it is a GraphQLInputObjectType and its fields are the same.
    If they are, return the existing 'GraphQLInputObjectType'. If not, raise an error.
    Otherwise, create a new 'GraphQLInputObjectType'.
    """
    input_object_type = GraphQLInputObjectType(
        name=name,
        fields=fields,
        description=description,
        extensions=extensions,
    )

    if name in GRAPHQL_TYPE_REGISTRY:
        compare_graphql_types(new_type=input_object_type, existing_type=GRAPHQL_TYPE_REGISTRY[name])
        return GRAPHQL_TYPE_REGISTRY[name]

    GRAPHQL_TYPE_REGISTRY[name] = input_object_type
    return input_object_type


def get_or_create_interface_type(
    *,
    name: str,
    fields: dict[str, GraphQLField] | FunctionEqualityWrapper[dict[str, GraphQLField]],
    description: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> GraphQLInterfaceType:
    """
    If a GraphQL Type with the same name already exists,
    check if it is a GraphQLInterfaceType and its fields are the same.
    If they are, return the existing 'GraphQLInterfaceType'. If not, raise an error.
    Otherwise, create a new 'GraphQLInterfaceType'.
    """
    interface_type = GraphQLInterfaceType(
        name=name,
        fields=fields,
        description=description,
        extensions=extensions,
    )

    if name in GRAPHQL_TYPE_REGISTRY:
        compare_graphql_types(new_type=interface_type, existing_type=GRAPHQL_TYPE_REGISTRY[name])
        return GRAPHQL_TYPE_REGISTRY[name]

    GRAPHQL_TYPE_REGISTRY[name] = interface_type
    return interface_type
