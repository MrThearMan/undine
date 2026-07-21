from __future__ import annotations

import datetime
import decimal
import uuid
from typing import Any, NamedTuple

import pytest
from graphql import GraphQLID, GraphQLNonNull, GraphQLObjectType, GraphQLString

from example_project.app.models import Project, Task
from tests.conftest import skip_if_async
from tests.helpers import parametrize_helper
from undine import Entrypoint, Field, GQLInfo, InterfaceField, InterfaceType, QueryType, RootType, UnionType
from undine.dataclasses import TypeRef
from undine.exceptions import (
    FederationKeyRequiresCustomResolverError,
    FunctionDispatcherError,
    MissingFederationFieldRefError,
    MissingFederationFieldResolverError,
)
from undine.federation import (
    ExternalDirective,
    FederationField,
    FederationType,
    KeyDirective,
    ShareableDirective,
    create_federation_schema,
)
from undine.pagination import OffsetPagination
from undine.relay import Connection

# Ref conversion


def test_federation_field__query_type_ref_list() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        tasks = FederationField(TaskType, many=True)

        @tasks.resolve
        def resolve_tasks(self, info):
            return []

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert "tasks: [TaskType!]!" in sdl


def test_federation_field__query_type_ref_single() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        task = FederationField(TaskType, many=False, nullable=True)

        @task.resolve
        def resolve_task(self, info: GQLInfo) -> Task | None:
            return None

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert "task: TaskType" in sdl


def test_federation_field__scalar_python_type() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        pages = FederationField(int)

        @pages.resolve
        def resolve_pages(self, info: GQLInfo) -> int:
            return 0

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert "pages: Int!" in sdl


def test_federation_field__interface_type_ref() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named]):
        name = Field()

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        named = FederationField(Named, nullable=True)

        @named.resolve
        def resolve_named(self, info: GQLInfo) -> Named | None:
            return None

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert "named: Named" in sdl


def test_federation_field__union_type_ref() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class ProjectType(QueryType[Project]):
        name = Field()

    class MyUnion(UnionType[TaskType, ProjectType]):
        pass

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        things = FederationField(MyUnion, nullable=True)

        @things.resolve
        def resolve_things(self, info: GQLInfo) -> list[Any]:
            return []

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert "things:" in sdl
    assert "MyUnion" in sdl


def test_federation_field__federation_type_ref() -> None:
    @KeyDirective(fields="id")
    class InnerExt(FederationType, schema_name="Inner"):
        id = FederationField(str)

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        inner = FederationField(InnerExt, nullable=True)

        @inner.resolve
        def resolve_inner(self, info: GQLInfo) -> InnerExt | None:
            return None

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert "inner: Inner" in sdl


def test_federation_field__graphql_type_ref() -> None:
    @KeyDirective(fields="id")
    class BookExt(FederationType, schema_name="Book"):
        id = FederationField(GraphQLNonNull(GraphQLID))

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert "id: ID!" in sdl


# Missing ref / bad ref


def test_federation_field__no_ref_raises_missing_ref_error() -> None:
    with pytest.raises(MissingFederationFieldRefError, match="isbn"):

        @KeyDirective(fields="isbn")
        class BookExt(FederationType, schema_name="Book"):
            isbn = FederationField()


def test_federation_field__connection_ref_raises_dispatcher_error() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    with pytest.raises(FunctionDispatcherError):

        @KeyDirective(fields="isbn")
        class BookExt(FederationType, schema_name="Book"):
            isbn = FederationField(str)
            tasks = FederationField(Connection(TaskType))


def test_federation_field__offset_pagination_ref_raises_dispatcher_error() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    with pytest.raises(FunctionDispatcherError):

        @KeyDirective(fields="isbn")
        class BookExt(FederationType, schema_name="Book"):
            isbn = FederationField(str)
            tasks = FederationField(OffsetPagination(TaskType))


# Resolver dispatch — three-case rule


def test_federation_field__computed_field_without_resolve_raises_at_schema_build() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        pages = FederationField(int)  # not in key, no @external, no @resolve

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    # graphql-core wraps the error in a TypeError during lazy thunk resolution.
    # Assert the underlying cause is our targeted exception, naming both class and field.
    with pytest.raises(TypeError) as exc_info:
        create_federation_schema(query=Query)

    cause = exc_info.value.__cause__
    assert isinstance(cause, MissingFederationFieldResolverError)
    assert "pages" in str(cause)
    assert "BookExt" in str(cause)


@skip_if_async
def test_federation_field__key_field_uses_attribute_lookup_default(undine_settings) -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)  # no @resolve, but part of key

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    # Building the field triggers the resolver factory; no MissingFederationFieldResolverError.
    book_type = schema.get_type("Book")
    assert isinstance(book_type, GraphQLObjectType)

    resolver = book_type.fields["isbn"].resolve

    class FakeRoot:
        isbn = "abc"

    assert resolver(FakeRoot(), None) == "abc"


@pytest.mark.asyncio
async def test_federation_field__key_field_uses_attribute_lookup_default__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)  # no @resolve, but part of key

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    # Building the field triggers the resolver factory; no MissingFederationFieldResolverError.
    book_type = schema.get_type("Book")
    assert isinstance(book_type, GraphQLObjectType)

    resolver = book_type.fields["isbn"].resolve

    class FakeRoot:
        isbn = "abc"

    assert await resolver(FakeRoot(), None) == "abc"


def test_federation_field__aliased_key_field_recognized_via_schema_name() -> None:
    @KeyDirective(fields="externalId")
    class BookExt(FederationType, schema_name="Book"):
        external_id = FederationField(str, schema_name="externalId")

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)

    book_type = schema.get_type("Book")
    assert isinstance(book_type, GraphQLObjectType)
    assert "externalId" in book_type.fields


@skip_if_async
def test_federation_field__external_field_uses_attribute_lookup_default() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        weight = FederationField(int) @ ExternalDirective()

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    book_type = schema.get_type("Book")
    assert isinstance(book_type, GraphQLObjectType)

    resolver = book_type.fields["weight"].resolve

    class FakeRoot:
        weight = 42

    assert resolver(FakeRoot(), None) == 42


@pytest.mark.asyncio
async def test_federation_field__external_field_uses_attribute_lookup_default__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        weight = FederationField(int) @ ExternalDirective()

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    book_type = schema.get_type("Book")
    assert isinstance(book_type, GraphQLObjectType)

    resolver = book_type.fields["weight"].resolve

    class FakeRoot:
        weight = 42

    assert await resolver(FakeRoot(), None) == 42


def test_federation_field__external_directive_appears_in_sdl() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        weight = FederationField(int) @ ExternalDirective()

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert "weight: Int! @external" in sdl


def test_federation_field__key_with_unknown_token_raises_at_class_definition_on_federation_type() -> None:
    with pytest.raises(FederationKeyRequiresCustomResolverError, match="notAField"):

        @KeyDirective(fields="notAField")
        class BookExt(FederationType, schema_name="Book"):
            isbn = FederationField(str)


def test_federation_field__resolve_decorator_wires_resolver() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        pages = FederationField(int)

        @pages.resolve
        def resolve_pages(self, info: GQLInfo) -> int:
            return 42

    class Query(RootType):
        task = Entrypoint(TaskType)

    # Just verify the schema builds with the wired resolver; runtime execution is Phase 4.
    schema = create_federation_schema(query=Query)
    assert schema.get_type("Book") is not None


def test_federation_field__shareable_directive_appears_in_sdl() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        tasks = FederationField(TaskType, many=True) @ ShareableDirective()

        @tasks.resolve
        def resolve_tasks(self, info: GQLInfo):
            return []

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert "tasks: [TaskType!]! @shareable" in sdl


# Scalar TypeRef conversion for supported Python scalar types


class ScalarRefParams(NamedTuple):
    python_type: type
    expected_scalar_name: str


@pytest.mark.parametrize(
    **parametrize_helper({
        "bool": ScalarRefParams(python_type=bool, expected_scalar_name="Boolean"),
        "float": ScalarRefParams(python_type=float, expected_scalar_name="Float"),
        "decimal": ScalarRefParams(python_type=decimal.Decimal, expected_scalar_name="Decimal"),
        "uuid": ScalarRefParams(python_type=uuid.UUID, expected_scalar_name="UUID"),
        "datetime": ScalarRefParams(python_type=datetime.datetime, expected_scalar_name="DateTime"),
        "date": ScalarRefParams(python_type=datetime.date, expected_scalar_name="Date"),
        "time": ScalarRefParams(python_type=datetime.time, expected_scalar_name="Time"),
    })
)
def test_federation_field__scalar_type_ref_conversion(python_type: type, expected_scalar_name: str) -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        value = FederationField(python_type)

        @value.resolve
        def resolve_value(self, info: GQLInfo) -> Any:
            return None

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert f"value: {expected_scalar_name}!" in sdl
    assert isinstance(BookExt.__field_map__["value"].ref, TypeRef)
    assert BookExt.__field_map__["value"].ref.value is python_type


def test_federation_field__function_ref_uses_function_resolver() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @FederationField
        def rating(self, info: GQLInfo) -> int:
            return 5

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert "rating: Int!" in sdl
    ref = BookExt.__field_map__["rating"].ref
    assert ref(None, None) == 5


def test_federation_field__decorator_with_parenthesis_assigns_ref() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @FederationField()
        def rating(self, info: GQLInfo) -> int:
            return 5

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert "rating: Int!" in sdl


@skip_if_async
def test_federation_field__non_key_directive_on_federation_type_is_skipped_for_resolver_dispatch() -> None:
    @KeyDirective(fields="isbn")
    @ShareableDirective()  # Position matters!
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    book_type = schema.get_type("Book")

    assert book_type is not None
    assert isinstance(book_type, GraphQLObjectType)

    resolver = book_type.fields["isbn"].resolve

    class FakeRoot:
        isbn = "abc"

    assert resolver(FakeRoot(), None) == "abc"


@pytest.mark.asyncio
async def test_federation_field__non_key_directive_on_federation_type_is_skipped_for_resolver_dispatch__async(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    @KeyDirective(fields="isbn")
    @ShareableDirective()  # Position matters!
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    book_type = schema.get_type("Book")

    assert book_type is not None
    assert isinstance(book_type, GraphQLObjectType)

    resolver = book_type.fields["isbn"].resolve

    class FakeRoot:
        isbn = "abc"

    assert await resolver(FakeRoot(), None) == "abc"


# FederationField descriptor and dunder behavior


def test_federation_field__repr_shows_ref() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    expected = "<undine.federation.federation_type.FederationField(ref=TypeRef(value=<class 'str'>, total=True))>"
    assert repr(BookExt.__field_map__["isbn"]) == expected


def test_federation_field__str_prints_sdl_line() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    assert str(BookExt.__field_map__["isbn"]) == "isbn: String!"


def test_federation_field__set_on_instance_updates_parameters() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    instance = BookExt(isbn="original")
    instance.isbn = "updated"

    assert instance.isbn == "updated"


def test_federation_field__set_on_class_raises_attribute_error() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

    with pytest.raises(AttributeError, match="isbn"):
        BookExt.__field_map__["isbn"].__set__(None, "value")


def test_federation_field__resolve_decorator_without_arguments_returns_wrapped_resolver() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        pages = FederationField(int)

        @pages.resolve()
        def resolve_pages(self, info: GQLInfo) -> int:
            return 42

    assert BookExt.__field_map__["pages"].resolver_func is not None


def test_federation_field__permissions_decorator_wires_permissions_func() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @isbn.permissions
        def isbn_permissions(self, info: GQLInfo, value: str) -> None:
            return None

    assert BookExt.__field_map__["isbn"].permissions_func is not None


def test_federation_field__permissions_decorator_without_arguments_returns_wrapped_permissions() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)

        @isbn.permissions()
        def isbn_permissions(self, info: GQLInfo, value: str) -> None:
            return None

    assert BookExt.__field_map__["isbn"].permissions_func is not None


# Description precedence in __connect__


def test_federation_field__description_from_attribute_docstring(undine_settings) -> None:
    undine_settings.ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS = True

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        """ISBN of the book."""

    assert BookExt.__field_map__["isbn"].description == "ISBN of the book."


def test_federation_field__description_from_user_overrides_docstring(undine_settings) -> None:
    undine_settings.ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS = True

    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str, description="Explicit description.")
        """Docstring for isbn."""

    assert BookExt.__field_map__["isbn"].description == "Explicit description."
