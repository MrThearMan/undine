from __future__ import annotations

from typing import Any, Callable, NamedTuple

import pytest

from example_project.app.models import Task
from tests.helpers import parametrize_helper
from undine import Entrypoint, Field, QueryType, RootType
from undine.federation import (
    AuthenticatedDirective,
    CacheTagDirective,
    ComposeDirectiveDirective,
    ContextDirective,
    CostDirective,
    InterfaceObjectDirective,
    KeyDirective,
    PolicyDirective,
    ShareableDirective,
    create_federation_schema,
)
from undine.federation.version import SUPPORTED_FEDERATION_VERSIONS


def test_service_query_returns_sdl(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)
    response = graphql("{ _service { sdl } }")

    assert response.has_errors is False, response.errors

    sdl = response.data["_service"]["sdl"]
    assert isinstance(sdl, str)
    assert len(sdl) > 0
    assert sdl == undine_settings.SCHEMA.extensions["undine_federation_sdl"]


def test_sdl__contains_extend_schema_link() -> None:
    @KeyDirective(fields="id")
    class TaskType(QueryType[Task]):
        id = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert "extend schema @link(" in sdl


def test_sdl__link_import_list_only_used_directives() -> None:
    @KeyDirective(fields="id")
    class TaskType(QueryType[Task]):
        id = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert '"@key"' in sdl
    assert '"@shareable"' not in sdl


def test_sdl__link_import_entries_prefixed_with_at() -> None:
    @KeyDirective(fields="id")
    class TaskType(QueryType[Task]):
        id = Field()
        name = Field() @ ShareableDirective()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert '"@key"' in sdl
    assert '"@shareable"' in sdl


def test_sdl__link_url_uses_federation_version(undine_settings) -> None:
    undine_settings.FEDERATION_VERSION = "2.14"

    @KeyDirective(fields="id")
    class TaskType(QueryType[Task]):
        id = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert "https://specs.apollo.dev/federation/v2.14" in sdl


def test_sdl__contains_key_usage_on_entity() -> None:
    @KeyDirective(fields="id")
    class TaskType(QueryType[Task]):
        id = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert "@key(" in sdl


def test_sdl__contains_shareable_usage() -> None:
    class TaskType(QueryType[Task]):
        name = Field() @ ShareableDirective()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert "@shareable" in sdl


def test_sdl__contains_service_type_definition() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert "type _Service" in sdl
    assert "sdl: String!" in sdl
    assert "_service: _Service!" in sdl


def test_sdl__doesnt_contain_builtin_scalars() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert "scalar _Any" not in sdl
    assert "_Any" not in sdl
    assert "scalar FieldSet" not in sdl
    assert "FieldSet" not in sdl


def test_sdl__omits_federation_directive_definitions() -> None:
    @KeyDirective(fields="id")
    class TaskType(QueryType[Task]):
        id = Field()
        name = Field() @ ShareableDirective()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert "directive @key" not in sdl
    assert "directive @link" not in sdl
    assert "directive @shareable" not in sdl


def test_link_import_list__contains_only_used_directive_classes() -> None:
    @KeyDirective(fields="id")
    class TaskType(QueryType[Task]):
        id = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert '"@key"' in sdl
    assert '"@link"' not in sdl


class _VersionParams(NamedTuple):
    version: str


class _BoundaryParams(NamedTuple):
    version: str
    build_query: Callable[[], type]
    expected_directives: set[str]
    schema_kwargs: dict[str, Any]


def _v20_query() -> type:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ ShareableDirective()

    return TaskType


def _v21_query() -> type:
    return _v20_query()


def _v23_query() -> type:
    @InterfaceObjectDirective()
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    return TaskType


def _v25_query() -> type:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ AuthenticatedDirective()

    return TaskType


def _v26_query() -> type:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ PolicyDirective(policies=[["p"]])

    return TaskType


def _v28_query() -> type:
    @ContextDirective(name="workspace")
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    return TaskType


def _v29_query() -> type:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ CostDirective(weight=1)

    return TaskType


def _v212_query() -> type:
    @CacheTagDirective(format="task")
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    return TaskType


@pytest.mark.parametrize(
    **parametrize_helper({
        version: _VersionParams(
            version=version,
        )
        for version in SUPPORTED_FEDERATION_VERSIONS
    })
)
def test_sdl__link_url_per_supported_version(undine_settings, version) -> None:
    undine_settings.FEDERATION_VERSION = version

    @KeyDirective(fields="id")
    class TaskType(QueryType[Task]):
        id = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    sdl = schema.extensions["undine_federation_sdl"]
    assert f"https://specs.apollo.dev/federation/v{version}" in sdl
    assert '"@key"' in sdl


@pytest.mark.parametrize(
    **parametrize_helper({
        "2.0 shareable": _BoundaryParams(
            version="2.0",
            build_query=_v20_query,
            expected_directives={"@key", "@shareable"},
            schema_kwargs={},
        ),
        "2.1 composeDirective": _BoundaryParams(
            version="2.1",
            build_query=_v21_query,
            expected_directives={"@key", "@shareable", "@composeDirective"},
            schema_kwargs={"schema_definition_directives": [ComposeDirectiveDirective(name="@custom")]},
        ),
        "2.3 interfaceObject": _BoundaryParams(
            version="2.3",
            build_query=_v23_query,
            expected_directives={"@key", "@interfaceObject"},
            schema_kwargs={},
        ),
        "2.5 authenticated": _BoundaryParams(
            version="2.5",
            build_query=_v25_query,
            expected_directives={"@key", "@authenticated"},
            schema_kwargs={},
        ),
        "2.6 policy": _BoundaryParams(
            version="2.6",
            build_query=_v26_query,
            expected_directives={"@key", "@policy"},
            schema_kwargs={},
        ),
        "2.8 context": _BoundaryParams(
            version="2.8",
            build_query=_v28_query,
            expected_directives={"@key", "@context"},
            schema_kwargs={},
        ),
        "2.9 cost": _BoundaryParams(
            version="2.9",
            build_query=_v29_query,
            expected_directives={"@key", "@cost"},
            schema_kwargs={},
        ),
        "2.12 cacheTag": _BoundaryParams(
            version="2.12",
            build_query=_v212_query,
            expected_directives={"@key", "@cacheTag"},
            schema_kwargs={},
        ),
    })
)
def test_sdl__link_import_contains_version_appropriate_directives(
    undine_settings, version, build_query, expected_directives, schema_kwargs
) -> None:
    undine_settings.FEDERATION_VERSION = version

    query_type = build_query()

    class Query(RootType):
        task = Entrypoint(query_type)

    schema = create_federation_schema(query=Query, **schema_kwargs)
    sdl = schema.extensions["undine_federation_sdl"]

    for directive_name in expected_directives:
        assert f'"{directive_name}"' in sdl, f"{directive_name} missing from @link import at {version}"
