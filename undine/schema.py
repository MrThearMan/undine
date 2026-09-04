from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from graphql import (
    DirectiveLocation,
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    GraphQLUnionType,
    validate_schema,
)

from undine.entrypoint import apply_default_cache_time
from undine.exceptions import UndineErrorGroup
from undine.settings import undine_settings
from undine.utils.graphql.caching import apply_request_caching
from undine.utils.graphql.type_registry import get_registered_directives
from undine.utils.graphql.undine_extensions import get_undine_interface_type
from undine.utils.graphql.utils import check_directives
from undine.utils.logging import logger
from undine.utils.visibility import apply_visibility

if TYPE_CHECKING:
    from graphql import GraphQLNamedType

    from undine import Directive, RootType

__all__ = [
    "create_schema",
]


def create_schema(
    *,
    query: type[RootType],
    mutation: type[RootType] | None = None,
    subscription: type[RootType] | None = None,
    description: str | None = None,
    schema_definition_directives: list[Directive] | None = None,
    extensions: dict[str, Any] | None = None,
) -> GraphQLSchema:
    """
    Creates the GraphQL schema.

    :param query: The `RootType` for the `Query` operations.
    :param mutation: The `RootType` for the `Mutation` operations.
    :param subscription: The `RootType` for the `Subscription` operations.
    :param description: The description for the schema.
    :param schema_definition_directives: The directives to add to the schema definition.
    :param extensions: The extensions for the schema.
    """
    started = time.perf_counter()
    extensions = extensions or {}
    schema_definition_directives = schema_definition_directives or []

    check_directives(schema_definition_directives, location=DirectiveLocation.SCHEMA)
    extensions[undine_settings.SCHEMA_DIRECTIVES_EXTENSIONS_KEY] = schema_definition_directives

    directives = get_registered_directives()

    logger.debug("Applying default cache time...")
    apply_default_cache_time(query)

    logger.debug("Creating Query type...")
    query_object_type: GraphQLObjectType = query.__output_type__()

    mutation_object_type: GraphQLObjectType | None = None
    if mutation is not None:
        logger.debug("Creating Mutation type...")
        mutation_object_type = mutation.__output_type__()

    subscription_object_type: GraphQLObjectType | None = None
    if subscription is not None:
        logger.debug("Creating Subscription type...")
        subscription_object_type = subscription.__output_type__()

    logger.debug("Creating GraphQL schema...")

    schema = GraphQLSchema(
        query=query_object_type,
        mutation=mutation_object_type,
        subscription=subscription_object_type,
        directives=directives,
        description=description,
        extensions=extensions,
    )

    for directive in schema_definition_directives:
        directive.__connected__(schema)

    schema = add_missing_interface_implementations(schema)

    sort_schema_types(schema)

    logger.debug("Validating GraphQL schema...")

    schema_validation_errors = validate_schema(schema)
    if schema_validation_errors:
        msg = "Schema validation failed"
        raise UndineErrorGroup(schema_validation_errors, msg=msg)

    logger.debug("Applying visibility...")
    apply_visibility(schema)

    logger.debug("Applying request caching hooks...")
    apply_request_caching(schema)

    elapsed = time.perf_counter() - started
    logger.debug(f"GraphQL schema created successfully in {elapsed}s!")

    return schema


def add_missing_interface_implementations(schema: GraphQLSchema) -> GraphQLSchema:
    """
    Force every concrete implementation of an `InterfaceType` used in the schema to be included
    in the schema, even if it isn't otherwise reachable from a root type.

    By default, `GraphQLSchema` only includes types reachable by traversing the root types, so an
    `InterfaceType` entrypoint whose implementing `QueryType`s have no `Entrypoint` of their own
    would otherwise end up referencing implementations that were never added to the schema.
    """
    # Looped rather than done in one pass: a freshly force-added implementation can itself
    # bring in fields of a new interface that then needs its own implementations force-added,
    # so keep reconstructing the schema until a pass finds nothing left to add.
    while True:
        missing_types: list[GraphQLObjectType] = []

        for named_type in schema.type_map.values():
            if not isinstance(named_type, GraphQLInterfaceType):
                continue

            interface_type = get_undine_interface_type(named_type)
            if interface_type is None:
                continue

            for implementation in interface_type.__concrete_implementations__():
                object_type = implementation.__output_type__()
                if object_type.name not in schema.type_map:
                    missing_types.append(object_type)

        if not missing_types:
            return schema

        kwargs = schema.to_kwargs()
        kwargs["types"] = (*(kwargs["types"] or ()), *missing_types)
        schema = GraphQLSchema(**kwargs)


def sort_schema_types(schema: GraphQLSchema) -> None:
    """Sort Schema types by type and name so that browsing GraphiQL is easier."""

    def key_func(item: tuple[str, GraphQLNamedType]) -> tuple[int, str]:
        match item[1]:
            # Put RootTypes at the end.
            case schema.query_type:
                type_order = 8
            case schema.mutation_type:
                type_order = 9
            case schema.subscription_type:
                type_order = 10
            # Sort more generic types first and then more specific types.
            case GraphQLScalarType():
                type_order = 1
            case GraphQLEnumType():
                type_order = 2
            case GraphQLInterfaceType():
                type_order = 3
            case GraphQLUnionType():
                type_order = 4
            case GraphQLObjectType():
                type_order = 5
            case GraphQLInputObjectType():
                type_order = 6
            case _:
                type_order = 7

        return type_order, item[0]

    schema.type_map = dict(sorted(schema.type_map.items(), key=key_func))
