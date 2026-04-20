from __future__ import annotations

import pytest
from graphql import (
    GraphQLField,
    GraphQLInterfaceType,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLString,
    GraphQLUnionType,
    OperationDefinitionNode,
    SelectionSetNode,
    parse,
)

from example_project.app.models import Project, Task
from undine import Entrypoint, Field, InterfaceField, InterfaceType, QueryType, RootType, create_schema
from undine.utils.graphql.caching import RequestCacheCalculator
from undine.utils.graphql.utils import get_fragment_definitions, get_operation_definition


def make_calculator(source: str) -> RequestCacheCalculator:
    doc = parse(source)
    operation = get_operation_definition(doc, None)
    fragments = get_fragment_definitions(doc)
    return RequestCacheCalculator(operation, fragments)


@pytest.mark.django_db
def test_request_cache_calculator__no_cache_time(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    calc = make_calculator("query($pk: Int!) { task(pk: $pk) { name } }")
    result = calc.run()
    assert result.cache_time == 0


@pytest.mark.django_db
def test_request_cache_calculator__inline_fragment_no_type_condition(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    source = "query($pk: Int!) { task(pk: $pk) { ... { name } } }"
    calc = make_calculator(source)
    result = calc.run()
    assert result.cache_time == 10


@pytest.mark.django_db
def test_request_cache_calculator__inline_fragment_with_type_condition(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    source = "query($pk: Int!) { task(pk: $pk) { ... on TaskType { name } } }"
    calc = make_calculator(source)
    result = calc.run()
    assert result.cache_time == 10


@pytest.mark.django_db
def test_request_cache_calculator__fragment_spread(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    source = "fragment TaskFields on TaskType { name } query($pk: Int!) { task(pk: $pk) { ...TaskFields } }"
    calc = make_calculator(source)
    result = calc.run()
    assert result.cache_time == 10


@pytest.mark.django_db
def test_request_cache_calculator__fragment_spread_already_visited(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)
        project = Entrypoint(ProjectType, cache_time=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    source = (
        "fragment Common on TaskType { name } "
        "query($t: Int! $p: Int!) { task(pk: $t) { ...Common } project(pk: $p) { ...Common } }"
    )
    calc = make_calculator(source)
    result = calc.run()
    assert result.cache_time == 10


@pytest.mark.django_db
def test_request_cache_calculator__fragment_spread_undefined(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    # Pass empty fragments dict so "Missing" won't be found
    source = "query($pk: Int!) { task(pk: $pk) { ...Missing } }"
    doc = parse(source)
    operation = get_operation_definition(doc, None)
    calc = RequestCacheCalculator(operation, {})
    result = calc.run()
    assert result.cache_time == 10


@pytest.mark.django_db
def test_request_cache_calculator__no_undine_field_extension(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    source = "query($pk: Int!) { task(pk: $pk) { __typename } }"
    calc = make_calculator(source)
    result = calc.run()
    assert result.cache_time == 10


@pytest.mark.django_db
def test_request_cache_calculator__interface_field_no_cache_time(undine_settings) -> None:
    class Named(InterfaceType, auto=False, cache_time=5):
        name = InterfaceField(GraphQLNonNull(GraphQLString))  # no cache_time on field

    @Named
    class TaskType(QueryType[Task], auto=False): ...

    class Query(RootType):
        named = Entrypoint(Named, cache_time=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    source = "query($pk: Int!) { named(pk: $pk) { name } }"
    calc = make_calculator(source)
    result = calc.run()
    assert result.cache_time == 10


@pytest.mark.django_db
def test_request_cache_calculator__object_type_with_cache_time(undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False, cache_time=5):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        project = Field()  # no cache_time on field, but ProjectType has cache_time=5

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    source = "query($pk: Int!) { task(pk: $pk) { project { name } } }"
    calc = make_calculator(source)
    result = calc.run()
    # Min of entrypoint (10) and ProjectType cache_time (5) = 5
    assert result.cache_time == 5


@pytest.mark.django_db
def test_request_cache_calculator__object_type_without_cache_time(undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):  # no cache_time
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        project = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    source = "query($pk: Int!) { task(pk: $pk) { project { name } } }"
    calc = make_calculator(source)
    result = calc.run()
    assert result.cache_time == 10  # stays at 10, ProjectType has no cache_time


def _make_bare_calculator() -> RequestCacheCalculator:
    op = OperationDefinitionNode(selection_set=SelectionSetNode(selections=()), directives=())
    return RequestCacheCalculator(op, {})


def test_parse_cache_time_from_type__object_type_no_undine_type() -> None:
    calc = _make_bare_calculator()
    calc.cache_time = 10
    gql_type = GraphQLObjectType("BareObj", fields={"x": GraphQLField(GraphQLString)})
    calc.parse_cache_time_from_type(gql_type)
    assert calc.cache_time == 10


def test_parse_cache_time_from_type__object_type_with_cache_time(undine_settings) -> None:
    calc = _make_bare_calculator()
    calc.cache_time = 10

    class FakeQT:
        __cache_time__ = 5
        __cache_per_user__ = False

    gql_type = GraphQLObjectType(
        "FakeObjCached",
        fields={"x": GraphQLField(GraphQLString)},
        extensions={undine_settings.QUERY_TYPE_EXTENSIONS_KEY: FakeQT},
    )
    calc.parse_cache_time_from_type(gql_type)
    assert calc.cache_time == 5


def test_parse_cache_time_from_type__interface_type_with_cache_time(undine_settings) -> None:
    calc = _make_bare_calculator()
    calc.cache_time = 10

    class FakeIT:
        __cache_time__ = 3
        __cache_per_user__ = True

    gql_type = GraphQLInterfaceType(
        "FakeIface",
        fields={"x": GraphQLField(GraphQLString)},
        extensions={undine_settings.INTERFACE_TYPE_EXTENSIONS_KEY: FakeIT},
    )
    calc.parse_cache_time_from_type(gql_type)
    assert calc.cache_time == 3
    assert calc.cache_per_user is True


def test_parse_cache_time_from_type__interface_type_no_cache_time(undine_settings) -> None:
    calc = _make_bare_calculator()
    calc.cache_time = 10

    class FakeIT:
        __cache_time__ = None
        __cache_per_user__ = False

    gql_type = GraphQLInterfaceType(
        "FakeIfaceNone",
        fields={"x": GraphQLField(GraphQLString)},
        extensions={undine_settings.INTERFACE_TYPE_EXTENSIONS_KEY: FakeIT},
    )
    calc.parse_cache_time_from_type(gql_type)
    assert calc.cache_time == 10


def test_parse_cache_time_from_type__union_type_with_cache_time(undine_settings) -> None:
    calc = _make_bare_calculator()
    calc.cache_time = 10

    class FakeUT:
        __cache_time__ = 7
        __cache_per_user__ = False

    member = GraphQLObjectType("UnionMember", fields={"x": GraphQLField(GraphQLString)})
    gql_type = GraphQLUnionType(
        "FakeUnion",
        types=[member],
        extensions={undine_settings.UNION_TYPE_EXTENSIONS_KEY: FakeUT},
    )
    calc.parse_cache_time_from_type(gql_type)
    assert calc.cache_time == 7


def test_parse_cache_time_from_type__union_type_no_cache_time(undine_settings) -> None:
    calc = _make_bare_calculator()
    calc.cache_time = 10

    class FakeUT:
        __cache_time__ = None
        __cache_per_user__ = False

    member = GraphQLObjectType("UnionMember2", fields={"x": GraphQLField(GraphQLString)})
    gql_type = GraphQLUnionType(
        "FakeUnion2",
        types=[member],
        extensions={undine_settings.UNION_TYPE_EXTENSIONS_KEY: FakeUT},
    )
    calc.parse_cache_time_from_type(gql_type)
    assert calc.cache_time == 10


def test_parse_cache_time_from_type__scalar_type_no_match(undine_settings) -> None:
    calc = _make_bare_calculator()
    calc.cache_time = 10
    # GraphQLString is a scalar — none of ObjectType/InterfaceType/UnionType cases match
    calc.parse_cache_time_from_type(GraphQLString)
    assert calc.cache_time == 10  # unchanged


def test_parse_cache_time_from_type__interface_type_no_undine_extension() -> None:
    calc = _make_bare_calculator()
    calc.cache_time = 10
    gql_type = GraphQLInterfaceType(
        "BareIface",
        fields={"x": GraphQLField(GraphQLString)},
    )
    calc.parse_cache_time_from_type(gql_type)
    assert calc.cache_time == 10


def test_parse_cache_time_from_type__union_type_no_undine_extension() -> None:
    calc = _make_bare_calculator()
    calc.cache_time = 10
    member = GraphQLObjectType("BareUnionMember3", fields={"x": GraphQLField(GraphQLString)})
    gql_type = GraphQLUnionType("BareUnion3", types=[member])
    calc.parse_cache_time_from_type(gql_type)
    assert calc.cache_time == 10


def test_calculate_cache_time__unknown_selection_type() -> None:
    calc = _make_bare_calculator()
    calc.cache_time = 10
    gql_type = GraphQLObjectType("FakeParent2", fields={"x": GraphQLField(GraphQLString)})
    calc.calculate_cache_time(gql_type, object())  # type: ignore[arg-type]
    assert calc.cache_time == 10  # unchanged
