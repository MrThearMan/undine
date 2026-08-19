from __future__ import annotations

from typing import Any

import pytest
from asgiref.sync import sync_to_async
from graphql import GraphQLUnionType

from example_project.app.models import Project, Task
from tests.conftest import skip_if_async
from tests.factories import ProjectFactory, TaskFactory
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType
from undine.exceptions import (
    FederationEntitiesFieldConflictError,
    FederationFieldSetTooComplexError,
    FederationKeyRequiresCustomResolverError,
    FederationMultipleKeysRequireCustomResolverError,
    GraphQLPermissionError,
)
from undine.federation import ExternalDirective, FederationField, FederationType, KeyDirective, create_federation_schema
from undine.federation.schema import find_resolvable_entities, find_resolvable_federation_types

# _Entity union presence / absence


def test_entities__union_contains_resolvable_query_types() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    @KeyDirective(fields="pk")
    class ProjectType(QueryType[Project]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)
        project = Entrypoint(ProjectType)

    schema = create_federation_schema(query=Query)

    union = schema.get_type("_Entity")
    assert isinstance(union, GraphQLUnionType)
    assert {t.name for t in union.types} == {"TaskType", "ProjectType"}


def test_entities__union_excludes_non_resolvable_key_types() -> None:
    @KeyDirective(fields="pk", resolvable=False)
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    assert schema.get_type("_Entity") is None
    assert "_entities" not in schema.query_type.fields


def test_entities__no_field_when_schema_has_no_resolvable_entities() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    assert schema.get_type("_Entity") is None
    assert "_entities" not in schema.query_type.fields


def test_entities__non_resolvable_stub_still_appears_in_sdl() -> None:
    @KeyDirective(fields="pk", resolvable=False)
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert 'type TaskType @key(fields: "pk", resolvable: false)' in sdl
    assert "_entities" not in sdl


def test_entities__find_resolvable_entities_matches_union_members() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    entities = find_resolvable_entities()
    assert entities == [TaskType]


# Query._entities field shape


def test_entities__entrypoint_signature_matches_apollo_spec() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    field = schema.query_type.fields["_entities"]

    assert str(field.type) == "[_Entity]!"
    assert set(field.args) == {"representations"}
    assert str(field.args["representations"].type) == "[_Any!]!"


def test_entities__sdl_omits_entities_field_per_apollo_spec() -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert "_entities(" not in sdl
    assert "_Any" not in sdl
    assert "_Entity" not in sdl


# _entities resolver behaviour


@pytest.mark.django_db
def test_entities__resolves_single_representation(graphql, undine_settings) -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    task = TaskFactory.create()

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) {
                ... on TaskType { pk name }
            }
        }
    """
    variables = {
        "reps": [{"__typename": "TaskType", "pk": task.pk}],
    }

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"pk": task.pk, "name": task.name}]


@pytest.mark.django_db
def test_entities__resolves_mixed_typenames(graphql, undine_settings) -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field()

    @KeyDirective(fields="pk")
    class ProjectType(QueryType[Project]):
        pk = Field()
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)
        project = Entrypoint(ProjectType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    task = TaskFactory.create()
    project = ProjectFactory.create()

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) {
                __typename
                ... on TaskType { pk name }
                ... on ProjectType { pk name }
            }
        }
    """
    variables = {
        "reps": [
            {"__typename": "TaskType", "pk": task.pk},
            {"__typename": "ProjectType", "pk": project.pk},
        ],
    }

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [
        {"__typename": "TaskType", "pk": task.pk, "name": task.name},
        {"__typename": "ProjectType", "pk": project.pk, "name": project.name},
    ]


@pytest.mark.django_db
def test_entities__empty_representations_returns_empty_list(graphql, undine_settings) -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = "query ($reps: [_Any!]!) { _entities(representations: $reps) { __typename } }"
    variables = {"reps": []}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == []


@pytest.mark.django_db
def test_entities__unknown_typename_yields_null_slot(graphql, undine_settings) -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { __typename }
        }
    """
    variables = {"reps": [{"__typename": "Bogus", "pk": 1}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [None]


# Default __resolve_reference__


@pytest.mark.django_db
def test_entities__default_resolver_performs_db_lookup(graphql, undine_settings) -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    task = TaskFactory.create(name="find-me")

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on TaskType { name } }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "pk": task.pk}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"name": "find-me"}]


@pytest.mark.django_db
def test_entities__default_resolver_translates_schema_name(graphql, undine_settings) -> None:
    @KeyDirective(fields="externalId")
    class TaskType(QueryType[Task]):
        external_id = Field("pk", schema_name="externalId")
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    task = TaskFactory.create(name="aliased")

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on TaskType { name } }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "externalId": task.pk}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"name": "aliased"}]


# Class-definition-time validation


def test_key_directive__compound_key_without_custom_resolver_raises() -> None:
    with pytest.raises(FederationFieldSetTooComplexError):

        @KeyDirective(fields="id name")
        class TaskType(QueryType[Task]):
            pk = Field()
            name = Field()


def test_key_directive__complex_fieldset_without_custom_resolver_raises() -> None:
    with pytest.raises(FederationFieldSetTooComplexError):

        @KeyDirective(fields="project { pk }")
        class TaskType(QueryType[Task]):
            pk = Field()


def test_key_directive__alias_fieldset_without_custom_resolver_raises() -> None:
    with pytest.raises(FederationFieldSetTooComplexError):

        @KeyDirective(fields="id: alias")
        class TaskType(QueryType[Task]):
            pk = Field()


def test_key_directive__complex_fieldset_with_custom_resolver_passes() -> None:
    @KeyDirective(fields="project { pk }")
    class TaskType(QueryType[Task]):
        pk = Field()

        @classmethod
        def __resolve_reference__(cls, representation: dict, info: GQLInfo) -> Task | None:
            return None

    assert TaskType.__resolve_reference__ is not None


def test_key_directive__unknown_token_raises() -> None:
    with pytest.raises(FederationKeyRequiresCustomResolverError):

        @KeyDirective(fields="notAField")
        class TaskType(QueryType[Task]):
            pk = Field()


def test_key_directive__multiple_resolvable_keys_without_custom_resolver_raises() -> None:
    with pytest.raises(FederationMultipleKeysRequireCustomResolverError):

        @KeyDirective(fields="pk")
        @KeyDirective(fields="name")
        class TaskType(QueryType[Task]):
            pk = Field()
            name = Field()


def test_key_directive__multiple_resolvable_keys_with_custom_resolver_passes() -> None:
    @KeyDirective(fields="pk")
    @KeyDirective(fields="name")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field()

        @classmethod
        def __resolve_reference__(cls, representation: dict, info: GQLInfo) -> Task | None:
            return None

    assert TaskType.__resolve_reference__ is not None


def test_key_directive__multiple_keys_with_only_one_resolvable_passes() -> None:
    @KeyDirective(fields="pk")
    @KeyDirective(fields="name", resolvable=False)
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field()

    assert TaskType is not None


# Custom __resolve_reference__


@pytest.mark.django_db
@skip_if_async
def test_entities__custom_resolve_reference_takes_precedence(graphql, undine_settings) -> None:
    stub = TaskFactory.create(name="stub")

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field()

        @classmethod
        def __resolve_reference__(cls, representation: dict[str, Any], info: GQLInfo) -> Task | None:
            return Task.objects.filter(pk=representation["pk"]).first()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on TaskType { pk name } }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "pk": stub.pk}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"pk": stub.pk, "name": stub.name}]


@pytest.mark.django_db(transaction=True)
async def test_entities__custom_resolve_reference_takes_precedence__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    stub = await sync_to_async(TaskFactory.create)(name="stub")

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field()

        @classmethod
        async def __resolve_reference__(cls, representation: dict[str, Any], info: GQLInfo) -> Task | None:
            return await Task.objects.filter(pk=representation["pk"]).afirst()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on TaskType { pk name } }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "pk": stub.pk}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"pk": stub.pk, "name": stub.name}]


@pytest.mark.django_db
def test_entities__resolve_reference_returning_none_yields_null(graphql, undine_settings) -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

        @classmethod
        def __resolve_reference__(cls, representation: dict, info: GQLInfo) -> Task | None:
            return None

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { __typename }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "pk": 1}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [None]


@pytest.mark.django_db
def test_entities__exception_in_resolve_reference_becomes_graphql_error(graphql, undine_settings) -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

        @classmethod
        def __resolve_reference__(cls, representation: dict, info: GQLInfo) -> Task | None:
            msg = "boom"
            raise RuntimeError(msg)

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { __typename }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "pk": 1}]}

    response = graphql(query, variables=variables)

    assert response.errors == [
        {
            "message": "boom",
            "path": ["_entities", 0],
            "extensions": {"status_code": 500},
        },
    ]


# Permissions on _entities


@pytest.mark.django_db
def test_entities__permissions_denies_returns_null_and_error(graphql, undine_settings) -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    task = TaskFactory.create()

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { __typename }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "pk": task.pk}]}

    response = graphql(query, variables=variables)

    assert response.errors == [
        {
            "message": "Permission denied.",
            "path": ["_entities", 0],
            "extensions": {"error_code": "PERMISSION_DENIED", "status_code": 403},
        }
    ]


@pytest.mark.django_db
def test_entities__permissions_allows_returns_entity(graphql, undine_settings) -> None:
    calls: list[int] = []

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            calls.append(instance.pk)

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    task = TaskFactory.create()

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on TaskType { pk } }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "pk": task.pk}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"pk": task.pk}]
    assert calls == [task.pk]


@pytest.mark.django_db
def test_entities__permissions_fires_for_every_returned_entity(graphql, undine_settings) -> None:
    calls: list[int] = []

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            calls.append(instance.pk)

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    task_1 = TaskFactory.create()
    task_2 = TaskFactory.create()
    task_3 = TaskFactory.create()

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on TaskType { pk } }
        }
    """
    variables = {
        "reps": [
            {"__typename": "TaskType", "pk": task_1.pk},
            {"__typename": "TaskType", "pk": task_2.pk},
            {"__typename": "TaskType", "pk": task_3.pk},
        ],
    }

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert sorted(calls) == sorted([task_1.pk, task_2.pk, task_3.pk])


@pytest.mark.django_db
def test_entities__permissions_matches_top_level_query_behavior(graphql, undine_settings) -> None:
    """Regression guard: entities the top-level resolver would reject are also rejected in `_entities`."""

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    task = TaskFactory.create()

    top_level_query = "query ($pk: Int!) { task(pk: $pk) { pk } }"
    top_level_variables = {"pk": task.pk}

    entities_query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { __typename }
        }
    """
    entities_variables = {"reps": [{"__typename": "TaskType", "pk": task.pk}]}

    top_level_response = graphql(top_level_query, variables=top_level_variables)
    entities_response = graphql(entities_query, variables=entities_variables)

    assert top_level_response.errors == [
        {
            "message": "Permission denied.",
            "path": ["task"],
            "extensions": {"error_code": "PERMISSION_DENIED", "status_code": 403},
        }
    ]
    assert entities_response.errors == [
        {
            "message": "Permission denied.",
            "path": ["_entities", 0],
            "extensions": {"error_code": "PERMISSION_DENIED", "status_code": 403},
        }
    ]


# Field-level permissions on _entities


@pytest.mark.django_db
def test_entities__field_permissions_denies_nulls_entity_and_errors(graphql, undine_settings) -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    task = TaskFactory.create()

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on TaskType { name } }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "pk": task.pk}]}

    response = graphql(query, variables=variables)

    assert response.data == {"_entities": [None]}
    assert response.errors == [
        {
            "message": "Permission denied.",
            "path": ["_entities", 0, "name"],
            "extensions": {"error_code": "PERMISSION_DENIED", "status_code": 403},
        }
    ]


@pytest.mark.django_db
def test_entities__field_permissions_allows_returns_value(graphql, undine_settings) -> None:
    calls: list[str] = []

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            calls.append(value)

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    task = TaskFactory.create(name="visible")

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on TaskType { name } }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "pk": task.pk}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"name": "visible"}]
    assert calls == ["visible"]


# Async dispatch parity


@pytest.mark.django_db(transaction=True)
async def test_entities__async_permissions_dispatch(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    calls: list[int] = []

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            calls.append(instance.pk)

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)()

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on TaskType { pk } }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "pk": task.pk}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"pk": task.pk}]
    assert calls == [task.pk]


@pytest.mark.django_db(transaction=True)
async def test_entities__async_field_permissions_dispatch(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    calls: list[str] = []

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field()

        @name.permissions
        async def name_permissions(self, info: GQLInfo, value: str) -> None:
            calls.append(value)

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="async-visible")

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on TaskType { name } }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "pk": task.pk}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"name": "async-visible"}]
    assert calls == ["async-visible"]


@pytest.mark.django_db(transaction=True)
async def test_entities__async_custom_resolve_reference(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field()

        @classmethod
        async def __resolve_reference__(cls, representation: dict, info: GQLInfo) -> Task | None:
            return await Task.objects.filter(pk=representation["pk"]).afirst()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="async-lookup")

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on TaskType { name } }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "pk": task.pk}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"name": "async-lookup"}]


# Runtime fallback + defensive paths


@pytest.mark.django_db
def test_entities__missing_typename_yields_null_slot(graphql, undine_settings) -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { __typename }
        }
    """
    variables = {"reps": [{"pk": 1}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [None]


@pytest.mark.django_db
def test_entities__non_string_typename_yields_null_slot(graphql, undine_settings) -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { __typename }
        }
    """
    variables = {"reps": [{"__typename": 123, "pk": 1}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [None]


# Registry nuances


def test_entities__query_type_with_mixed_resolvable_keys_is_included() -> None:
    @KeyDirective(fields="pk", resolvable=False)
    @KeyDirective(fields="name")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    union = schema.get_type("_Entity")
    assert isinstance(union, GraphQLUnionType)
    assert {t.name for t in union.types} == {"TaskType"}


def test_entities__repeated_key_directives_produce_one_union_member() -> None:
    @KeyDirective(fields="pk")
    @KeyDirective(fields="name")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field()

        @classmethod
        def __resolve_reference__(cls, representation: dict, info: GQLInfo) -> Task | None:
            return None

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    union = schema.get_type("_Entity")
    assert isinstance(union, GraphQLUnionType)
    assert [t.name for t in union.types] == ["TaskType"]


# Async: defensive paths


@pytest.mark.django_db(transaction=True)
async def test_entities__async_missing_typename_yields_null_slot(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { __typename }
        }
    """
    variables = {"reps": [{"pk": 1}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [None]


@pytest.mark.django_db(transaction=True)
async def test_entities__async_resolve_reference_returning_none_yields_null(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

        @classmethod
        async def __resolve_reference__(cls, representation: dict, info: GQLInfo) -> Task | None:
            return None

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { __typename }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "pk": 1}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [None]


@pytest.mark.django_db(transaction=True)
async def test_entities__async_exception_in_permissions_becomes_graphql_error(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)()

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { __typename }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "pk": task.pk}]}

    response = await graphql_async(query, variables=variables)

    assert response.errors == [
        {
            "message": "Permission denied.",
            "path": ["_entities", 0],
            "extensions": {"error_code": "PERMISSION_DENIED", "status_code": 403},
        }
    ]


@pytest.mark.django_db(transaction=True)
async def test_entities__async_uses_sync_custom_resolve_reference(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    task = await sync_to_async(TaskFactory.create)(name="sync-resolver")

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field()

        @classmethod
        def __resolve_reference__(cls, representation: dict, info: GQLInfo) -> Task | None:
            return task

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on TaskType { name } }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "pk": task.pk}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"name": "sync-resolver"}]


# Multiple keys with first non-resolvable exercises directive iteration


@pytest.mark.django_db
def test_entities__non_resolvable_key_before_resolvable_key(graphql, undine_settings) -> None:
    @KeyDirective(fields="name")
    @KeyDirective(fields="pk", resolvable=False)
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    task = TaskFactory.create(name="find-by-name")

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on TaskType { name } }
        }
    """
    variables = {"reps": [{"__typename": "TaskType", "name": "find-by-name"}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"name": task.name}]


# Conflict error


def test_entities__entrypoint_conflict_raises() -> None:
    def _entities_resolver(root, info) -> list:
        return []

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)
        _entities = Entrypoint(_entities_resolver)

    with pytest.raises(FederationEntitiesFieldConflictError):
        create_federation_schema(query=Query)


# FederationType union membership


def test_entities__union_contains_resolvable_federation_types() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    union = schema.get_type("_Entity")
    assert isinstance(union, GraphQLUnionType)
    assert {t.name for t in union.types} == {"TaskType", "Book"}


def test_entities__find_resolvable_federation_types_matches_union_members() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    entities = find_resolvable_federation_types()
    assert entities == [BookExt]


# FederationType default __resolve_reference__


@pytest.mark.django_db
def test_entities__federation_type_default_resolver_constructs_instance(graphql, undine_settings) -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        title = FederationField(str) @ ExternalDirective()

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) {
                __typename
                ... on Book { isbn title }
            }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "9780000000000", "title": "The Book"}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [
        {"__typename": "Book", "isbn": "9780000000000", "title": "The Book"},
    ]


@pytest.mark.django_db
def test_entities__federation_type_default_resolver_translates_schema_names(graphql, undine_settings) -> None:
    """Representation keys use schema names; the default resolver must map them back to Python field names."""

    @KeyDirective(fields="externalId")
    class BookExt(FederationType, schema_name="Book"):
        external_id = FederationField(str, schema_name="externalId")
        book_title = FederationField(str, schema_name="bookTitle") @ ExternalDirective()

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) {
                ... on Book { externalId bookTitle }
            }
        }
    """
    variables = {"reps": [{"__typename": "Book", "externalId": "x-1", "bookTitle": "aliased"}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"externalId": "x-1", "bookTitle": "aliased"}]


@pytest.mark.django_db
def test_entities__federation_type_default_resolver_ignores_unknown_keys(graphql, undine_settings) -> None:
    """Reps can carry keys not declared on the FederationType (including __typename); the resolver drops them."""
    captured: dict[str, Any] = {}

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @classmethod
        def __permissions__(cls, instance: BookExt, info: GQLInfo) -> None:
            captured.update(instance.__parameters__)

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { isbn } }
        }
    """
    variables = {
        "reps": [{"__typename": "Book", "isbn": "9780000000000", "somethingElse": 42}],
    }

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"isbn": "9780000000000"}]
    assert captured == {"isbn": "9780000000000"}


# FederationType custom __resolve_reference__


@pytest.mark.django_db
def test_entities__federation_type_custom_resolve_reference_takes_precedence(graphql, undine_settings) -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        title = FederationField(str) @ ExternalDirective()

        @classmethod
        def __resolve_reference__(cls, representation: dict[str, Any], info: GQLInfo) -> BookExt:
            return cls(isbn=representation["isbn"], title="from-custom-resolver")

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { isbn title } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "9780000000000"}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"isbn": "9780000000000", "title": "from-custom-resolver"}]


@pytest.mark.django_db
def test_entities__federation_type_resolve_reference_returning_none_yields_null(graphql, undine_settings) -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @classmethod
        def __resolve_reference__(cls, representation: dict[str, Any], info: GQLInfo) -> BookExt | None:
            return None

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { __typename }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "9780000000000"}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [None]


@pytest.mark.django_db
def test_entities__federation_type_exception_in_resolve_reference_becomes_graphql_error(
    graphql, undine_settings
) -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @classmethod
        def __resolve_reference__(cls, representation: dict[str, Any], info: GQLInfo) -> BookExt:
            msg = "boom"
            raise RuntimeError(msg)

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { __typename }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "9780000000000"}]}

    response = graphql(query, variables=variables)

    assert response.errors == [
        {
            "message": "boom",
            "path": ["_entities", 0],
            "extensions": {"status_code": 500},
        },
    ]


# FederationType permissions


@pytest.mark.django_db
def test_entities__federation_type_permissions_denies_returns_null_and_error(graphql, undine_settings) -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @classmethod
        def __permissions__(cls, instance: BookExt, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { __typename }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "9780000000000"}]}

    response = graphql(query, variables=variables)

    assert response.errors == [
        {
            "message": "Permission denied.",
            "path": ["_entities", 0],
            "extensions": {"error_code": "PERMISSION_DENIED", "status_code": 403},
        },
    ]


@pytest.mark.django_db
def test_entities__federation_type_permissions_allows_returns_entity(graphql, undine_settings) -> None:
    calls: list[str] = []

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @classmethod
        def __permissions__(cls, instance: BookExt, info: GQLInfo) -> None:
            calls.append(instance.isbn)

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { isbn } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "9780000000000"}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"isbn": "9780000000000"}]
    assert calls == ["9780000000000"]


# Mixed union dispatch (regression for _build_entity_union.resolve_type)


@pytest.mark.django_db
def test_entities__resolves_query_type_and_federation_type_in_one_call(graphql, undine_settings) -> None:
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field()

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        title = FederationField(str) @ ExternalDirective()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    task = TaskFactory.create()

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) {
                __typename
                ... on TaskType { pk name }
                ... on Book { isbn title }
            }
        }
    """
    variables = {
        "reps": [
            {"__typename": "TaskType", "pk": task.pk},
            {"__typename": "Book", "isbn": "978", "title": "A Book"},
        ],
    }

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [
        {"__typename": "TaskType", "pk": task.pk, "name": task.name},
        {"__typename": "Book", "isbn": "978", "title": "A Book"},
    ]


# FederationType async parity


@pytest.mark.django_db(transaction=True)
async def test_entities__async_federation_type_default_resolver(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        title = FederationField(str) @ ExternalDirective()

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { isbn title } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "978", "title": "async"}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"isbn": "978", "title": "async"}]


@pytest.mark.django_db(transaction=True)
async def test_entities__async_federation_type_async_custom_resolve_reference(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        title = FederationField(str) @ ExternalDirective()

        @classmethod
        async def __resolve_reference__(cls, representation: dict[str, Any], info: GQLInfo) -> BookExt:
            return cls(isbn=representation["isbn"], title="async-custom")

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { isbn title } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "978"}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"isbn": "978", "title": "async-custom"}]


@pytest.mark.django_db(transaction=True)
async def test_entities__async_federation_type_permissions_dispatch(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    calls: list[str] = []

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @classmethod
        async def __permissions__(cls, instance: BookExt, info: GQLInfo) -> None:
            calls.append(instance.isbn)

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { isbn } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "978"}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"isbn": "978"}]
    assert calls == ["978"]


@pytest.mark.django_db(transaction=True)
async def test_entities__async_federation_type_resolve_reference_returning_none_yields_null(
    graphql_async, undine_settings
) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @classmethod
        async def __resolve_reference__(cls, representation: dict, info: GQLInfo) -> BookExt | None:
            return None

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { __typename }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "978"}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [None]


@pytest.mark.django_db(transaction=True)
async def test_entities__async_federation_type_exception_in_resolve_reference_becomes_graphql_error(
    graphql_async, undine_settings
) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @classmethod
        async def __resolve_reference__(cls, representation: dict, info: GQLInfo) -> BookExt | None:
            msg = "boom-async"
            raise RuntimeError(msg)

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { __typename }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "978"}]}

    response = await graphql_async(query, variables=variables)

    assert response.errors == [
        {
            "message": "boom-async",
            "path": ["_entities", 0],
            "extensions": {"status_code": 500},
        },
    ]
