from __future__ import annotations

import pytest
from graphql import GraphQLNonNull, GraphQLString, parse

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
    assert result.cache_time == 10


@pytest.mark.django_db
def test_request_cache_calculator__interface_field_with_cache_time(undine_settings) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString), cache_time=5)

    @Named
    class TaskType(QueryType[Task], auto=False): ...

    class Query(RootType):
        named = Entrypoint(Named, cache_time=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    source = "query($pk: Int!) { named(pk: $pk) { name } }"
    calc = make_calculator(source)
    result = calc.run()
    assert result.cache_time == 5


@pytest.mark.django_db
def test_request_cache_calculator__interface_field_without_cache_time(undine_settings) -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

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
def test_request_cache_calculator__typename(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    source = "query($pk: Int!) { task(pk: $pk) { __typename } }"
    calc = make_calculator(source)
    result = calc.run()
    assert result.cache_time == 10
