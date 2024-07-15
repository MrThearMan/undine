from __future__ import annotations

from typing import Any, Collection

from graphql import GraphQLDirective, GraphQLNamedType, GraphQLObjectType, GraphQLSchema, specified_directives

from undine.fields import Entrypoint
from undine.utils.reflection import get_members
from undine.utils.text import get_docstring, get_schema_name

__all__ = [
    "create_schema",
]


def create_schema(  # noqa: PLR0913
    *,
    query_class: type | None = None,
    mutation_class: type | None = None,
    # subscription_class: type | None = None,
    schema_description: str | None = None,
    additional_types: Collection[GraphQLNamedType] | None = None,
    additional_directives: Collection[GraphQLDirective] | None = None,
    query_extensions: dict[str, Any] | None = None,
    mutation_extensions: dict[str, Any] | None = None,
    # subscription_extensions: dict[str, Any] | None = None,
    schema_extensions: dict[str, Any] | None = None,
) -> GraphQLSchema:
    """Creates the GraphQL schema."""
    query_object_type = create_object_type(query_class, query_extensions)
    mutation_object_type = create_object_type(mutation_class, mutation_extensions)
    # subscription_object_type = create_object_type(subscription_class, subscription_extensions)

    return GraphQLSchema(
        query=query_object_type,
        mutation=mutation_object_type,
        subscription=None,
        types=additional_types,
        directives=(*specified_directives, *additional_directives) if additional_directives else None,
        description=schema_description,
        extensions=schema_extensions,
    )


def create_object_type(cls: type | None, extensions: dict[str, Any] | None = None) -> GraphQLObjectType | None:
    if cls is None:
        return None

    return GraphQLObjectType(
        cls.__name__,
        fields={get_schema_name(name): entr.get_graphql_field() for name, entr in get_members(cls, Entrypoint)},
        extensions=extensions,
        description=get_docstring(cls),
    )
