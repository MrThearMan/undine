from __future__ import annotations

from inspect import cleandoc
from typing import TYPE_CHECKING, Any

from graphql import (
    DirectiveLocation,
    GraphQLArgument,
    GraphQLDirective,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLInputObjectType,
    GraphQLInt,
    GraphQLInterfaceType,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLUnionType,
    specified_directives,
    specified_scalar_types,
)

from undine.exceptions import GraphQLDuplicateTypeError
from undine.utils.registy import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Collection

    from graphql import (
        GraphQLAbstractType,
        GraphQLField,
        GraphQLInputField,
        GraphQLScalarSerializer,
        GraphQLScalarValueParser,
        GraphQLTypeResolver,
    )
    from graphql.type.definition import GraphQLInputFieldOutType

    from undine import GQLInfo
    from undine.typing import UniquelyNamedGraphQLElement
    from undine.utils.reflection import FunctionEqualityWrapper


__all__ = [
    "GRAPHQL_REGISTRY",
    "get_or_create_graphql_directive",
    "get_or_create_graphql_enum",
    "get_or_create_graphql_input_object_type",
    "get_or_create_graphql_interface_type",
    "get_or_create_graphql_object_type",
    "get_or_create_graphql_scalar",
    "get_or_create_graphql_union",
    "get_registered_directives",
    "register_builtins",
]


GRAPHQL_REGISTRY: Registry[str, UniquelyNamedGraphQLElement] = Registry()
"""
Caches created GraphQL elements by their names so that they can be reused during schema creation
since a GraphQL Schema cannot contain multiple elements with the same name.
"""


def get_or_create_graphql_object_type(
    *,
    name: str,
    fields: dict[str, GraphQLField] | FunctionEqualityWrapper[dict[str, GraphQLField]],
    interfaces: Collection[GraphQLInterfaceType] | None = None,
    description: str | None = None,
    is_type_of: Callable[[Any, GQLInfo], bool] | None = None,
    extensions: dict[str, Any] | None = None,
) -> GraphQLObjectType:
    """
    Either create a new 'GraphQLObjectType' or get an existing one with the same name.
    Checks that the existing element is indeed a 'GraphQLObjectType', and raises an error
    if it is not the same.
    """
    object_type = GraphQLObjectType(
        name=name,
        fields=fields,
        interfaces=interfaces,
        description=description,
        is_type_of=is_type_of,  # type: ignore[arg-type]
        extensions=extensions,
    )

    if name in GRAPHQL_REGISTRY:
        existing = GRAPHQL_REGISTRY[name]

        if (
            not isinstance(existing, GraphQLObjectType)
            or existing._fields != object_type._fields
            or existing._interfaces != object_type._interfaces  # noqa: SLF001
            or existing.is_type_of != object_type.is_type_of
            or existing.description != object_type.description
            or existing.extensions != object_type.extensions
        ):
            raise GraphQLDuplicateTypeError(
                name=name,
                type_new=object_type,
                type_existing=existing,
            )

        return existing

    GRAPHQL_REGISTRY[name] = object_type
    return object_type


def get_or_create_graphql_input_object_type(
    *,
    name: str,
    fields: dict[str, GraphQLInputField] | FunctionEqualityWrapper[dict[str, GraphQLInputField]],
    description: str | None = None,
    extensions: dict[str, Any] | None = None,
    out_type: GraphQLInputFieldOutType | None = None,
) -> GraphQLInputObjectType:
    """
    Either create a new 'GraphQLInputObjectType' or get an existing one with the same name.
    Checks that the existing element is indeed a 'GraphQLInputObjectType', and raises an error
    if it is not the same.
    """
    input_object_type = GraphQLInputObjectType(
        name=name,
        fields=fields,
        description=description,
        extensions=extensions,
        out_type=out_type,
    )

    if name in GRAPHQL_REGISTRY:
        existing = GRAPHQL_REGISTRY[name]

        if (
            not isinstance(existing, GraphQLInputObjectType)
            or existing._fields != input_object_type._fields
            or existing.description != input_object_type.description
            or existing.extensions != input_object_type.extensions
            or existing.out_type != input_object_type.out_type
        ):
            raise GraphQLDuplicateTypeError(
                name=name,
                type_new=input_object_type,
                type_existing=existing,
            )

        return existing

    GRAPHQL_REGISTRY[name] = input_object_type
    return input_object_type


def get_or_create_graphql_interface_type(
    *,
    name: str,
    fields: dict[str, GraphQLField] | FunctionEqualityWrapper[dict[str, GraphQLField]],
    interfaces: Collection[GraphQLInterfaceType] | None = None,
    resolve_type: GraphQLTypeResolver | None = None,
    description: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> GraphQLInterfaceType:
    """
    Either create a new 'GraphQLInterfaceType' or get an existing one with the same name.
    Checks that the existing element is indeed a 'GraphQLInterfaceType', and raises an error
    if it is not the same.
    """
    interface_type = GraphQLInterfaceType(
        name=name,
        fields=fields,
        interfaces=interfaces,
        resolve_type=resolve_type,
        description=description,
        extensions=extensions,
    )

    if name in GRAPHQL_REGISTRY:
        existing = GRAPHQL_REGISTRY[name]

        if (
            not isinstance(existing, GraphQLInterfaceType)
            or existing._fields != interface_type._fields
            or existing._interfaces != interface_type._interfaces  # noqa: SLF001
            or existing.resolve_type != interface_type.resolve_type
            or existing.description != interface_type.description
            or existing.extensions != interface_type.extensions
        ):
            raise GraphQLDuplicateTypeError(
                name=name,
                type_new=interface_type,
                type_existing=existing,
            )

        return existing

    GRAPHQL_REGISTRY[name] = interface_type
    return interface_type


def get_or_create_graphql_enum(
    *,
    name: str,
    values: dict[str, str | GraphQLEnumValue],
    description: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> GraphQLEnumType:
    """
    Either create a new 'GraphQLEnumType' or get an existing one with the same name.
    Checks that the existing element is indeed a 'GraphQLEnumType', and raises an error
    if it is not the same.
    """
    for key, value in values.items():
        if isinstance(value, str):
            values[key] = GraphQLEnumValue(value=key, description=value)

    enum = GraphQLEnumType(
        name=name,
        values=values,
        description=description,
        extensions=extensions,
    )

    if name in GRAPHQL_REGISTRY:
        existing = GRAPHQL_REGISTRY[name]

        if (
            not isinstance(existing, GraphQLEnumType)
            or existing.values != enum.values
            or existing.description != enum.description
            or existing.extensions != enum.extensions
        ):
            raise GraphQLDuplicateTypeError(
                name=name,
                type_new=enum,
                type_existing=existing,
            )

        return existing

    GRAPHQL_REGISTRY[name] = enum
    return enum


def get_or_create_graphql_union(
    *,
    name: str,
    types: list[GraphQLObjectType] | FunctionEqualityWrapper[list[GraphQLObjectType]],
    resolve_type: Callable[[Any, GQLInfo, GraphQLAbstractType], str | None] | None = None,
    description: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> GraphQLUnionType:
    """
    Either create a new 'GraphQLUnionType' or get an existing one with the same name.
    Checks that the existing element is indeed a GraphQLUnionType, and raises an error
    if it is not the same.
    """
    union = GraphQLUnionType(
        name=name,
        types=types,
        resolve_type=resolve_type,  # type: ignore[arg-type]
        description=description,
        extensions=extensions,
    )

    if name in GRAPHQL_REGISTRY:
        existing = GRAPHQL_REGISTRY[name]

        if (
            not isinstance(existing, GraphQLUnionType)
            or existing._types != union._types  # noqa: SLF001
            or existing.resolve_type != union.resolve_type
            or existing.description != union.description
            or existing.extensions != union.extensions
        ):
            raise GraphQLDuplicateTypeError(
                name=name,
                type_new=union,
                type_existing=existing,
            )

        return existing

    GRAPHQL_REGISTRY[name] = union
    return union


def get_or_create_graphql_scalar(
    *,
    name: str,
    serialize: GraphQLScalarSerializer | None = None,
    parse_value: GraphQLScalarValueParser | None = None,
    description: str | None = None,
    specified_by_url: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> GraphQLScalarType:
    """
    Either create a new 'GraphQLScalarType' or get an existing one with the same name.
    Checks that the existing element is indeed a 'GraphQLScalarType', and raises an error
    if it is not the same.
    """
    scalar = GraphQLScalarType(
        name=name,
        serialize=serialize,
        parse_value=parse_value,
        description=description,
        specified_by_url=specified_by_url,
        extensions=extensions,
    )

    if name in GRAPHQL_REGISTRY:
        existing = GRAPHQL_REGISTRY[name]

        if (
            not isinstance(existing, GraphQLScalarType)
            or existing.serialize != scalar.serialize
            or existing.parse_value != scalar.parse_value
            or existing.description != scalar.description
            or existing.specified_by_url != scalar.specified_by_url
            or existing.extensions != scalar.extensions
        ):
            raise GraphQLDuplicateTypeError(
                name=name,
                type_new=scalar,
                type_existing=existing,
            )

        return existing

    GRAPHQL_REGISTRY[name] = scalar
    return scalar


def get_or_create_graphql_directive(
    *,
    name: str,
    locations: list[DirectiveLocation],
    args: dict[str, GraphQLArgument] | None = None,
    is_repeatable: bool = False,
    description: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> GraphQLDirective:
    """
    Either create a new 'GraphQLDirective' or get an existing one with the same name.
    Checks that the existing element is indeed a 'GraphQLDirective', and raises an error
    if it is not the same.
    """
    directive = GraphQLDirective(
        name=name,
        locations=locations,
        args=args,
        is_repeatable=is_repeatable,
        description=description,
        extensions=extensions,
    )

    if name in GRAPHQL_REGISTRY:
        existing = GRAPHQL_REGISTRY[name]

        if not isinstance(existing, GraphQLDirective) or directive != existing:
            raise GraphQLDuplicateTypeError(
                name=name,
                type_new=directive,
                type_existing=existing,
            )

        return existing

    GRAPHQL_REGISTRY[name] = directive
    return directive


GraphQLComplexityDirective = GraphQLDirective(
    name="complexity",
    locations=[DirectiveLocation.FIELD_DEFINITION],
    args={
        "value": GraphQLArgument(
            GraphQLNonNull(GraphQLInt),
            out_name="value",
        ),
    },
    description=cleandoc(
        """
        Indicate the complexity of resolving a field, counted towards
        the maximum query complexity of resolving a root type field.
        """
    ),
)
"""Used to indicate the complexity of resolving a given field. See `Field.complexity`."""


GraphQLOneOfDirective = GraphQLDirective(
    name="oneOf",
    locations=[DirectiveLocation.INPUT_OBJECT],
    description="Indicates exactly one field must be supplied and this field must not be `null`.",
)
"""Used to indicate an Input Object is a OneOf Input Object."""


def register_builtins() -> None:
    for name, scalar in specified_scalar_types.items():
        GRAPHQL_REGISTRY[name] = scalar

    for directive in specified_directives:
        GRAPHQL_REGISTRY[directive.name] = directive

    GRAPHQL_REGISTRY[GraphQLComplexityDirective.name] = GraphQLComplexityDirective
    GRAPHQL_REGISTRY[GraphQLOneOfDirective.name] = GraphQLOneOfDirective


def get_registered_directives() -> tuple[GraphQLDirective, ...]:
    return tuple(value for value in GRAPHQL_REGISTRY.values() if isinstance(value, GraphQLDirective))
