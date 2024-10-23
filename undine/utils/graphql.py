"""Utils that should be sorted into different files later."""

from __future__ import annotations

from typing import TYPE_CHECKING

from graphql import GraphQLEnumType, GraphQLEnumValue, GraphQLError, GraphQLList, GraphQLNonNull

from undine.errors.exceptions import GraphQLCantCreateEnumError, GraphQLDuplicateEnumError
from undine.registies import GRAPHQL_ENUM_REGISTRY
from undine.utils.text import to_pascal_case

if TYPE_CHECKING:
    from django.db import models

    from undine.typing import TGraphQLType


__all__ = [
    "create_graphql_enum",
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


def create_graphql_enum(
    field: models.CharField,
    *,
    name: str | None = None,
    description: str | None = None,
) -> GraphQLEnumType:
    """
    Creates a GraphQL enum for the given field.
    If a field with the same name already exists, the already created enum is returned,
    unless that enum's values are different than the new enum's, in which case an error is raised.
    """
    if not field.choices:
        raise GraphQLCantCreateEnumError(field=field)

    if name is None:
        # Generate a name for an enum based on the field it is used in.
        # This is required, since CharField doesn't know the name of the enum it is used in.
        # Use `TextChoicesField` instead to get more consistent naming.
        name = field.model.__name__ + to_pascal_case(field.name, validate=False) + "Choices"

    enum = GraphQLEnumType(
        name=name,
        values={value.upper(): GraphQLEnumValue(value=value, description=label) for value, label in field.choices},
        description=description or getattr(field, "help_text", None) or None,
    )

    if name in GRAPHQL_ENUM_REGISTRY:
        new_values = enum.values
        exisisting_values = GRAPHQL_ENUM_REGISTRY[name].values
        if new_values != exisisting_values:
            raise GraphQLDuplicateEnumError(enum_name=name, values_1=list(new_values), values_2=list(exisisting_values))

        return GRAPHQL_ENUM_REGISTRY[name]

    GRAPHQL_ENUM_REGISTRY[name] = enum
    return enum


def add_default_status_codes(errors: list[GraphQLError]) -> list[GraphQLError]:
    for error in errors:
        error.extensions.setdefault("status_code", 400)
    return errors
