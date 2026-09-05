from __future__ import annotations

from inspect import cleandoc

import pytest
from graphql import GraphQLUnionType

from example_project.app.models import Task
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType
from undine.exceptions import (
    FederationFieldSetTooComplexError,
    FederationKeyRequiresCustomResolverError,
    FederationMultipleKeysRequireCustomResolverError,
    MissingFederationKeysError,
    MissingFederationReferenceResolverError,
)
from undine.federation import (
    ExternalDirective,
    FederationField,
    FederationType,
    KeyDirective,
    ShareableDirective,
    create_federation_schema,
)
from undine.federation.federation_type import FEDERATION_TYPE_REGISTRY

# Class-definition-time behaviour


def test_federation_type__key_directive_applies_without_raising() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    assert any(isinstance(d, KeyDirective) for d in BookExt.__directives__)


def test_federation_type__registered_in_federation_type_registry() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    assert FEDERATION_TYPE_REGISTRY["Book"] is BookExt


def test_federation_type__schema_name_defaults_to_class_name() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType):
        isbn = FederationField(str)

    assert BookExt.__schema_name__ == "BookExt"


# SDL emission


def test_federation_type__appears_in_sdl_as_extend_type() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert 'extend type Book @key(fields: "isbn")' in sdl


def test_federation_type__sdl_extends_the_owned_type() -> None:
    # A resolvable FederationType contributes fields to an entity owned by another subgraph,
    # so its SDL renders as `extend type Foo @key(fields: "x") { x: String! }`.
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert 'extend type Book @key(fields: "isbn") {\n  isbn: String!\n}' in sdl


def test_federation_type__multiple_key_directives_produce_two_key_usages_in_sdl() -> None:
    @KeyDirective(fields="isbn")
    @KeyDirective(fields="upc")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        upc = FederationField(str)

        @classmethod
        def __resolve_reference__(cls, representation, info):
            return cls(**{k: v for k, v in representation.items() if k != "__typename"})

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert '@key(fields: "isbn")' in sdl
    assert '@key(fields: "upc")' in sdl


def test_federation_type__resolvable_appears_in_entity_union() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    union = schema.get_type("_Entity")

    assert isinstance(union, GraphQLUnionType)
    assert "Book" in {t.name for t in union.types}


def test_federation_type__non_resolvable_key_excluded_from_entity_union_but_still_in_sdl() -> None:
    @KeyDirective(fields="isbn", resolvable=False)
    class BookStub(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    # A resolvable FederationType references the stub via a FederationField, keeping BookStub
    # reachable from the schema (matches how Apollo stubs are used per the subgraph spec).
    @KeyDirective(fields="pk")
    class OrderExt(FederationType, schema_name="Order"):
        pk = FederationField(str)
        book = FederationField(BookStub)

        @book.resolve
        def resolve_book(self, info):
            return None

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]
    union = schema.get_type("_Entity")

    assert isinstance(union, GraphQLUnionType)
    assert "Book" not in {t.name for t in union.types}
    assert "Order" in {t.name for t in union.types}
    assert 'type Book @key(fields: "isbn", resolvable: false)' in sdl


def test_federation_type__stub_with_explicit_id_field_renders_correctly() -> None:
    # Interpretation of the plan's "stub reference pattern" test — key field is
    # declared explicitly by the user.
    @KeyDirective(fields="id", resolvable=False)
    class BookStub(FederationType, schema_name="Book"):
        id = FederationField(str)

    @KeyDirective(fields="pk")
    class OrderExt(FederationType, schema_name="Order"):
        pk = FederationField(str)
        book = FederationField(BookStub)

        @book.resolve
        def resolve_book(self, info):
            return None

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert 'type Book @key(fields: "id", resolvable: false)' in sdl
    assert "id: String!" in sdl


# Missing keys


def test_federation_type__missing_key_raises_at_schema_creation() -> None:
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    with pytest.raises(MissingFederationKeysError):
        create_federation_schema(query=Query)


# Instance construction


def test_federation_type__instance_attribute_access_via_field_get() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    instance = BookExt(isbn="123")
    assert instance.isbn == "123"


def test_federation_type__accessing_unpopulated_computed_field_raises_attribute_error() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        rating = FederationField(int)

        @rating.resolve
        def resolve_rating(self, info):
            return 5

    instance = BookExt(isbn="123")
    with pytest.raises(ValueError, match="rating"):
        _ = instance.rating


# @KeyDirective validation on FederationType (mirrors QueryType arm)


def test_federation_type__key_with_unknown_token_raises_at_class_definition() -> None:
    with pytest.raises(FederationKeyRequiresCustomResolverError, match="notAField"):

        @KeyDirective(fields="notAField")
        class BookExt(FederationType, schema_name="Book"):
            isbn = FederationField(str)


def test_federation_type__compound_key_raises_field_set_too_complex() -> None:
    with pytest.raises(FederationFieldSetTooComplexError):

        @KeyDirective(fields="isbn upc")
        class BookExt(FederationType, schema_name="Book"):
            isbn = FederationField(str)
            upc = FederationField(str)


def test_federation_type__nested_key_raises_field_set_too_complex() -> None:
    with pytest.raises(FederationFieldSetTooComplexError):

        @KeyDirective(fields="project { pk }")
        class BookExt(FederationType, schema_name="Book"):
            project = FederationField(str)


def test_federation_type__aliased_key_raises_field_set_too_complex() -> None:
    with pytest.raises(FederationFieldSetTooComplexError):

        @KeyDirective(fields="id: alias")
        class BookExt(FederationType, schema_name="Book"):
            id = FederationField(str)


def test_federation_type__two_resolvable_keys_without_custom_resolver_raises() -> None:
    with pytest.raises(FederationMultipleKeysRequireCustomResolverError):

        @KeyDirective(fields="isbn")
        @KeyDirective(fields="upc")
        class BookExt(FederationType, schema_name="Book"):
            isbn = FederationField(str)
            upc = FederationField(str)


def test_federation_type__two_keys_with_custom_resolver_pass_validation() -> None:
    @KeyDirective(fields="isbn")
    @KeyDirective(fields="upc")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        upc = FederationField(str)

        @classmethod
        def __resolve_reference__(cls, representation, info):
            return cls(**{k: v for k, v in representation.items() if k != "__typename"})

    assert BookExt.__schema_name__ == "Book"


def test_federation_type__resolvable_false_with_unknown_token_does_not_raise() -> None:
    @KeyDirective(fields="notAField", resolvable=False)
    class BookStub(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    assert BookStub.__schema_name__ == "Book"


def test_federation_type__nested_key_with_custom_resolver_passes_validation() -> None:
    @KeyDirective(fields="project { pk }")
    class BookExt(FederationType, schema_name="Book"):
        project = FederationField(str)

        @classmethod
        def __resolve_reference__(cls, representation, info):
            return cls(**{k: v for k, v in representation.items() if k != "__typename"})

    assert BookExt.__schema_name__ == "Book"


# Integration


def test_federation_type__service_sdl_uses_extend_keyword() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert "extend type Book" in sdl


# Field(FederationType) — QueryType-side references to entity stubs


def test_federation_type__field_ref_from_query_type_renders_stub_type() -> None:
    @KeyDirective(fields="id", resolvable=False)
    class UserStub(FederationType, schema_name="User"):
        id = FederationField(int)

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        assigned_to = Field(UserStub)

        @assigned_to.resolve
        def resolve_assigned_to(root: Task, info: GQLInfo) -> dict:
            return {"id": 1}

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert "assignedTo: User!" in sdl
    assert 'type User @key(fields: "id", resolvable: false)' in sdl


def test_federation_type__field_ref_from_query_type_nullable_renders_optional() -> None:
    @KeyDirective(fields="id", resolvable=False)
    class UserStub(FederationType, schema_name="User"):
        id = FederationField(int)

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        assigned_to = Field(UserStub, nullable=True)

        @assigned_to.resolve
        def resolve_assigned_to(root: Task, info: GQLInfo) -> dict | None:
            return None

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert "assignedTo: User" in sdl
    assert "assignedTo: User!" not in sdl


def test_federation_type__field_ref_from_query_type_resolver_returns_reference() -> None:
    @KeyDirective(fields="id", resolvable=False)
    class UserStub(FederationType, schema_name="User"):
        id = FederationField(int)

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        assigned_to = Field(UserStub)

        @assigned_to.resolve
        def resolve_assigned_to(root: Task, info: GQLInfo) -> dict:
            return {"id": 42}

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    task_output = schema.get_type("TaskType")
    field = task_output.fields["assignedTo"]  # type: ignore[union-attr]
    result = field.resolve(Task(), None)
    assert result == {"id": 42}


def test_federation_type__field_ref_from_query_type_without_resolver_raises() -> None:
    @KeyDirective(fields="id", resolvable=False)
    class UserStub(FederationType, schema_name="User"):
        id = FederationField(int)

    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        assigned_to = Field(UserStub)

    class Query(RootType):
        task = Entrypoint(TaskType)

    # graphql-core wraps the error in a TypeError during lazy thunk resolution.
    with pytest.raises(TypeError) as exc_info:
        create_federation_schema(query=Query)

    cause = exc_info.value.__cause__
    assert isinstance(cause, MissingFederationReferenceResolverError)
    assert "assigned_to" in str(cause)
    assert "UserStub" in str(cause)


# Metaclass directives= kwarg


def test_federation_type__directives_class_kwarg_connects_directive() -> None:
    shareable = ShareableDirective()

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book", directives=[shareable]):
        isbn = FederationField(str)

    assert shareable in BookExt.__directives__.data


# Metaclass dunder methods


def test_federation_type__str_prints_sdl_object_type() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    assert str(BookExt) == cleandoc(
        """
        extend type Book @key(fields: "isbn") {
          isbn: String!
        }
        """
    )


def test_federation_type__contains_checks_field_map() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    assert "isbn" in BookExt
    assert "not_a_field" not in BookExt


# FederationFieldResolver runtime behavior


@pytest.mark.django_db
def test_federation_type__resolver_returns_none_for_nullable_missing_value(graphql, undine_settings) -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        note = FederationField(str, nullable=True) @ ExternalDirective()

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { isbn note } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "978", "note": None}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"isbn": "978", "note": None}]


@pytest.mark.django_db
def test_federation_type__resolver_raises_for_non_nullable_missing_value(graphql, undine_settings) -> None:
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
    # title is explicitly null; resolver returns None from a non-nullable field → raises.
    variables = {"reps": [{"__typename": "Book", "isbn": "978", "title": None}]}

    response = graphql(query, variables=variables)

    assert response.errors == [
        {
            "message": "'Book.title' returned null, but field is not nullable.",
            "path": ["_entities", 0, "title"],
            "extensions": {"error_code": "FIELD_NOT_NULLABLE", "status_code": 400},
        }
    ]


@pytest.mark.django_db
def test_federation_type__resolver_runs_permissions_func(graphql, undine_settings) -> None:
    calls: list = []

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        title = FederationField(str) @ ExternalDirective()

        @title.permissions
        def title_permissions(self, info: GQLInfo, value: str) -> None:
            calls.append(value)

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { title } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "978", "title": "hello"}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert calls == ["hello"]


@pytest.mark.django_db(transaction=True)
async def test_federation_type__async_resolver_returns_none_for_nullable_missing_value(
    graphql_async, undine_settings
) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        note = FederationField(str, nullable=True) @ ExternalDirective()

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { isbn note } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "978", "note": None}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"isbn": "978", "note": None}]


@pytest.mark.django_db(transaction=True)
async def test_federation_type__async_resolver_raises_for_non_nullable_missing_value(
    graphql_async, undine_settings
) -> None:
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
            _entities(representations: $reps) { ... on Book { title } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "978", "title": None}]}

    response = await graphql_async(query, variables=variables)

    assert response.errors == [
        {
            "message": "'Book.title' returned null, but field is not nullable.",
            "path": ["_entities", 0, "title"],
            "extensions": {"error_code": "FIELD_NOT_NULLABLE", "status_code": 400},
        }
    ]


@pytest.mark.django_db(transaction=True)
async def test_federation_type__async_resolver_runs_sync_permissions_func(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    calls: list = []

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        title = FederationField(str) @ ExternalDirective()

        @title.permissions
        def title_permissions(self, info: GQLInfo, value: str) -> None:
            calls.append(value)

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { title } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "978", "title": "async-hello"}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert calls == ["async-hello"]


@pytest.mark.django_db(transaction=True)
async def test_federation_type__async_resolver_runs_async_permissions_func(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    calls: list = []

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        title = FederationField(str) @ ExternalDirective()

        @title.permissions
        async def title_permissions(self, info: GQLInfo, value: str) -> None:
            calls.append(value)

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { title } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "978", "title": "async-hello"}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert calls == ["async-hello"]


# FederationFieldFunctionResolver runtime behavior


@pytest.mark.django_db
def test_federation_type__function_resolver_runs_sync(graphql, undine_settings) -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @FederationField
        def rating(root, info: GQLInfo) -> int:
            return root.isbn.count("9")

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { rating } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "9789"}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"rating": 2}]


@pytest.mark.django_db
def test_federation_type__function_resolver_runs_permissions(graphql, undine_settings) -> None:
    calls: list = []

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @FederationField
        def rating(root, info: GQLInfo) -> int:
            return 5

        @rating.permissions
        def rating_permissions(root, info: GQLInfo, value: int) -> None:
            calls.append(value)

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { rating } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "978"}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert calls == [5]


@pytest.mark.django_db(transaction=True)
async def test_federation_type__async_function_resolver_runs(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @FederationField
        async def rating(root, info: GQLInfo) -> int:
            return len(root.isbn)

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { rating } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "9781234"}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"rating": 7}]


@pytest.mark.django_db(transaction=True)
async def test_federation_type__async_function_resolver_runs_sync_permissions(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    calls: list = []

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @FederationField
        async def rating(root, info: GQLInfo) -> int:
            return 5

        @rating.permissions
        def rating_permissions(root, info: GQLInfo, value: int) -> None:
            calls.append(value)

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { rating } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "978"}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert calls == [5]


@pytest.mark.django_db(transaction=True)
async def test_federation_type__async_function_resolver_runs_async_permissions(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    calls: list = []

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @FederationField
        async def rating(root, info: GQLInfo) -> int:
            return 5

        @rating.permissions
        async def rating_permissions(root, info: GQLInfo, value: int) -> None:
            calls.append(value)

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { rating } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "978"}]}

    response = await graphql_async(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert calls == [5]


@pytest.mark.django_db
def test_federation_type__function_resolver_without_root_or_info_params(graphql, undine_settings) -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @FederationField
        def rating() -> int:
            return 7

    class TaskType(QueryType[Task]):
        pk = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_federation_schema(query=Query)

    query = """
        query ($reps: [_Any!]!) {
            _entities(representations: $reps) { ... on Book { rating } }
        }
    """
    variables = {"reps": [{"__typename": "Book", "isbn": "978"}]}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.data["_entities"] == [{"rating": 7}]


# Visibility


def test_federation_type__is_visible_default_returns_true() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    assert BookExt.__is_visible__(None) is True  # type: ignore[arg-type]


def test_federation_type__is_visible_override_returns_false() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @classmethod
        def __is_visible__(cls, request) -> bool:
            return False

    assert BookExt.__is_visible__(None) is False  # type: ignore[arg-type]
