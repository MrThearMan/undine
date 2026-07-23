from __future__ import annotations

from typing import TYPE_CHECKING, Any

from undine.exceptions import (
    FederationEntitiesFieldConflictError,
    FederationFeatureVersionError,
    FederationServiceFieldConflictError,
    UnsupportedFederationVersionError,
)
from undine.federation import KeyDirective
from undine.federation.directives import LinkDirective
from undine.federation.entities import make_entities_entrypoint
from undine.federation.federation_type import FEDERATION_TYPE_REGISTRY
from undine.federation.service import make_service_entrypoint
from undine.federation.validation import validate_federation_types_have_keys
from undine.federation.version import (
    SUPPORTED_FEDERATION_VERSIONS,
    is_supported_federation_version,
    is_supported_in_federation_version,
)
from undine.query import QUERY_TYPE_REGISTRY
from undine.schema import create_schema
from undine.settings import undine_settings
from undine.utils.graphql.undine_extensions import get_undine_schema_directives

if TYPE_CHECKING:
    from graphql import GraphQLDirective, GraphQLField, GraphQLNamedType, GraphQLSchema

    from undine import Directive, QueryType
    from undine.entrypoint import RootType
    from undine.federation import FederationType

__all__ = [
    "create_federation_schema",
]


def create_federation_schema(
    *,
    query: type[RootType],
    mutation: type[RootType] | None = None,
    subscription: type[RootType] | None = None,
    description: str | None = None,
    schema_definition_directives: list[Directive] | None = None,
    extensions: dict[str, Any] | None = None,
) -> GraphQLSchema:
    """Create a Federation 2 subgraph-compliant GraphQL schema."""
    version = undine_settings.FEDERATION_VERSION
    if not is_supported_federation_version(version):
        raise UnsupportedFederationVersionError(
            version=version,
            supported_versions=list(SUPPORTED_FEDERATION_VERSIONS),
        )

    if subscription is not None and not is_supported_in_federation_version("2.4"):
        raise FederationFeatureVersionError(feature="Subscription root type", min_version="2.4")

    validate_federation_types_have_keys()

    if "_service" in query.__entrypoint_map__:
        raise FederationServiceFieldConflictError(query=query)
    if "_entities" in query.__entrypoint_map__:
        raise FederationEntitiesFieldConflictError(query=query)

    query.__entrypoint_map__["_service"] = make_service_entrypoint(query)

    resolvable_entities = find_resolvable_entities()
    resolvable_federation_types = find_resolvable_federation_types()

    if resolvable_entities or resolvable_federation_types:
        query.__entrypoint_map__["_entities"] = make_entities_entrypoint(
            query,
            resolvable_entities,
            resolvable_federation_types,
        )

    schema = create_schema(
        query=query,
        mutation=mutation,
        subscription=subscription,
        description=description,
        schema_definition_directives=schema_definition_directives,
        extensions=extensions,
    )

    link_directive = LinkDirective.autogenerate()
    link_directive.__connected__(schema)
    schema_definition_directives = get_undine_schema_directives(schema)
    if schema_definition_directives is not None:  # pragma: no branch
        schema_definition_directives.insert(0, link_directive)

    sdl = undine_settings.SDL_PRINTER.print_schema(
        schema,
        directive_filter=skip_federation_directive_definitions,
        type_filter=skip_federation_type_definitions,
        field_filter=skip_federation_field_definitions,
        extend_schema=True,
    )
    schema.extensions[undine_settings.FEDERATION_SDL_EXTENSIONS_KEY] = sdl
    return schema


def skip_federation_directive_definitions(directive: GraphQLDirective) -> bool:
    if not undine_settings.SDL_PRINTER.default_directive_filter(directive):
        return False
    return not directive.extensions.get(undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY, False)


def skip_federation_type_definitions(named_type: GraphQLNamedType) -> bool:
    if not undine_settings.SDL_PRINTER.default_type_filter(named_type):
        return False
    return not named_type.extensions.get(undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY, False)


def skip_federation_field_definitions(field: GraphQLField) -> bool:
    if not undine_settings.SDL_PRINTER.default_field_filter(field):
        return False
    return not field.extensions.get(undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY, False)


def find_resolvable_entities() -> list[type[QueryType]]:
    entities: list[type[QueryType]] = []
    for query_type in QUERY_TYPE_REGISTRY.values():
        for directive in query_type.__directives__:
            if isinstance(directive, KeyDirective) and directive.__parameters__["resolvable"]:
                entities.append(query_type)
                break
    return entities


def find_resolvable_federation_types() -> list[type[FederationType]]:
    entities: list[type[FederationType]] = []
    for federation_type in FEDERATION_TYPE_REGISTRY.values():
        for directive in federation_type.__directives__:
            if isinstance(directive, KeyDirective) and directive.__parameters__["resolvable"]:
                entities.append(federation_type)
                break
    return entities
