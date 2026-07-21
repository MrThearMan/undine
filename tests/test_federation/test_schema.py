from __future__ import annotations

import pytest
from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from example_project.app.models import Task
from undine import Directive, DirectiveArgument, Entrypoint, Field, QueryType, RootType
from undine.exceptions import (
    FederationFeatureVersionError,
    FederationServiceFieldConflictError,
    UnsupportedFederationVersionError,
)
from undine.federation import create_federation_schema
from undine.federation.version import SUPPORTED_FEDERATION_VERSIONS, parse_version


def test_create_federation_schema__returns_valid_schema() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    assert schema.query_type is not None


def test_create_federation_schema__conflict_with_existing_service_entrypoint() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    def _service_resolver(root, info) -> str:
        return ""

    class Query(RootType):
        task = Entrypoint(TaskType)
        _service = Entrypoint(_service_resolver)

    with pytest.raises(FederationServiceFieldConflictError):
        create_federation_schema(query=Query)


def test_create_federation_schema__merges_user_schema_directives() -> None:
    class MyDirective(
        Directive,
        locations=[DirectiveLocation.SCHEMA],
        schema_name="my",
    ):
        note = DirectiveArgument(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(
        query=Query,
        schema_definition_directives=[MyDirective(note="hi")],
    )
    sdl = schema.extensions["undine_federation_sdl"]

    assert "@link(" in sdl
    assert '@my(note: "hi")' in sdl


def test_create_federation_schema__service_field_present() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    query_type = schema.query_type

    assert "_service" in query_type.fields
    assert str(query_type.fields["_service"].type) == "_Service!"


def test_create_federation_schema__accepts_empty_federation() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert "@link(" in sdl
    assert "import: []" not in sdl


def test_create_federation_schema__subscription_at_2_4_passes(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.4"

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Subscription(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query, subscription=Subscription)
    assert schema.subscription_type is not None


def test_create_federation_schema__subscription_below_2_4_raises(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.3"

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Subscription(RootType):
        task = Entrypoint(TaskType)

    with pytest.raises(FederationFeatureVersionError):
        create_federation_schema(query=Query, subscription=Subscription)


def test_create_federation_schema__no_subscription_ignores_version_gate(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.0"

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    assert schema.subscription_type is None


def test_create_federation_schema__unsupported_version_error_lists_versions_in_numeric_order(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "bogus"

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    with pytest.raises(UnsupportedFederationVersionError) as exc_info:
        create_federation_schema(query=Query)

    message = str(exc_info.value)
    positions = [message.index(f"'{version}'") for version in SUPPORTED_FEDERATION_VERSIONS]
    assert positions == sorted(positions), (
        "Supported versions should appear in numeric order matching SUPPORTED_FEDERATION_VERSIONS, "
        f"but got positions {positions} for versions {list(SUPPORTED_FEDERATION_VERSIONS)}"
    )
    assert parse_version(SUPPORTED_FEDERATION_VERSIONS[0]) < parse_version(SUPPORTED_FEDERATION_VERSIONS[-1])
