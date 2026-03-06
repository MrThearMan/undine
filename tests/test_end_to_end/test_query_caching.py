from __future__ import annotations

import json
import re
from contextlib import contextmanager
from typing import Any, Generator
from unittest.mock import patch

import pytest
from django.core.cache import caches
from graphql import GraphQLNonNull, GraphQLString, Undefined

from example_project.app.models import Project, Task
from tests.factories import ProjectFactory, TaskFactory, UserFactory
from undine import Entrypoint, Field, InterfaceField, InterfaceType, MutationType, QueryType, RootType, create_schema
from undine.dataclasses import CacheControlResults
from undine.utils.graphql.caching import RequestCacheCalculator


@pytest.fixture(autouse=True)
def _clear_sse_cache(undine_settings):
    """Handle clearing the cache between runs so that cache data is not shared between tests."""
    yield
    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]
    cache.clear()


def get_cache_key(*, source: str, variables: dict[str, Any], user_id: int | None = Undefined) -> str:
    source = re.sub(r"\s+", "", source, flags=re.UNICODE)
    variables = json.dumps(variables, separators=(",", ":"))
    key = f"undine-cache|{source}|{variables}"
    if user_id is not Undefined:
        key = f"{key}|{user_id}"
    return key


@contextmanager
def catch_cache_results() -> Generator[CacheControlResults, None, None]:
    original_run = RequestCacheCalculator.run

    return_value = CacheControlResults(cache_time=Undefined, cache_per_user=Undefined)  # type: ignore[arg-type]

    def run(self: RequestCacheCalculator) -> CacheControlResults:
        results = original_run(self)
        return_value.cache_time = results.cache_time
        return_value.cache_per_user = results.cache_per_user
        return results

    with patch.object(RequestCacheCalculator, "run", new=run):
        yield return_value


@pytest.mark.django_db
def test_end_to_end__caching__entrypoint_cacheable(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_for_seconds=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Test task")

    query = """
        query($pk: Int!) {
          task(pk: $pk) {
            name
          }
        }
    """
    variables = {"pk": task.pk}

    with catch_cache_results() as results:
        response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.results == {"name": "Test task"}

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]

    key = get_cache_key(source=query, variables=variables)
    assert cache.get(key) is not None

    assert results.cache_time == 10
    assert results.cache_per_user is False


@pytest.mark.django_db
def test_end_to_end__caching__entrypoint_cacheable__per_user(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_for_seconds=10, cache_per_user=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Test task")

    query = """
        query($pk: Int!) {
          task(pk: $pk) {
            name
          }
        }
    """
    variables = {"pk": task.pk}

    user_1 = UserFactory.create(username="foo")
    user_2 = UserFactory.create(username="bar")

    graphql.force_login(user_1)

    with catch_cache_results() as results:
        response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.results == {"name": "Test task"}

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]

    key_user = get_cache_key(source=query, variables=variables, user_id=user_1.pk)
    assert cache.get(key_user) is not None

    key_user = get_cache_key(source=query, variables=variables, user_id=user_2.pk)
    assert cache.get(key_user) is None

    assert results.cache_time == 10
    assert results.cache_per_user is True


@pytest.mark.django_db
def test_end_to_end__caching__entrypoint_cacheable__per_user__anonymous(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_for_seconds=10, cache_per_user=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Test task")

    query = """
        query($pk: Int!) {
          task(pk: $pk) {
            name
          }
        }
    """
    variables = {"pk": task.pk}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.results == {"name": "Test task"}

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]

    key_all = get_cache_key(source=query, variables=variables)
    assert cache.get(key_all) is None

    key_user = get_cache_key(source=query, variables=variables, user_id=None)
    assert cache.get(key_user) is not None


@pytest.mark.django_db
def test_end_to_end__caching__entrypoint_not_cacheable__field_ignored(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field(cache_for_seconds=10)

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Test task")

    query = """
        query($pk: Int!) {
          task(pk: $pk) {
            name
          }
        }
    """
    variables = {"pk": task.pk}

    with catch_cache_results() as results:
        response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.results == {"name": "Test task"}

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]

    key = get_cache_key(source=query, variables=variables)
    assert cache.get(key) is None

    # Entrypoint is not cacheable, so the field is ignored
    assert results.cache_time == 0
    assert results.cache_per_user is False


@pytest.mark.django_db
def test_end_to_end__caching__entrypoint_not_cacheable__type_ignored(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, cache_for_seconds=10):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Test task")

    query = """
        query($pk: Int!) {
          task(pk: $pk) {
            name
          }
        }
    """
    variables = {"pk": task.pk}

    response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.results == {"name": "Test task"}

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]

    key = get_cache_key(source=query, variables=variables)
    assert cache.get(key) is None


@pytest.mark.django_db
def test_end_to_end__caching__field_cacheable(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field(cache_for_seconds=5)

    class Query(RootType):
        task = Entrypoint(TaskType, cache_for_seconds=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Test task")

    query = """
        query($pk: Int!) {
          task(pk: $pk) {
            name
          }
        }
    """
    variables = {"pk": task.pk}

    with catch_cache_results() as results:
        response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.results == {"name": "Test task"}

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]

    key = get_cache_key(source=query, variables=variables)
    assert cache.get(key) is not None

    # Use more restrictive cache time from the field
    assert results.cache_time == 5
    assert results.cache_per_user is False


@pytest.mark.django_db
def test_end_to_end__caching__field_not_cacheable(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field(cache_for_seconds=0)

    class Query(RootType):
        task = Entrypoint(TaskType, cache_for_seconds=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Test task")

    query = """
        query($pk: Int!) {
          task(pk: $pk) {
            name
          }
        }
    """
    variables = {"pk": task.pk}

    with catch_cache_results() as results:
        response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.results == {"name": "Test task"}

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]

    key = get_cache_key(source=query, variables=variables)
    assert cache.get(key) is None

    # Use more restrictive cache time from the field
    assert results.cache_time == 0
    assert results.cache_per_user is False


@pytest.mark.django_db
def test_end_to_end__caching__field_type_not_cacheable(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False, cache_for_seconds=0):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        task = Entrypoint(TaskType, cache_for_seconds=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    project = ProjectFactory.create(name="Test project")
    task = TaskFactory.create(name="Test task", project=project)

    query = """
        query($pk: Int!) {
          task(pk: $pk) {
            name
            project {
              name
            }
          }
        }
    """
    variables = {"pk": task.pk}

    with catch_cache_results() as results:
        response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.results == {"name": "Test task", "project": {"name": "Test project"}}

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]

    key = get_cache_key(source=query, variables=variables)
    assert cache.get(key) is None

    # Use more restrictive cache time from the project field type
    assert results.cache_time == 0
    assert results.cache_per_user is False


@pytest.mark.django_db
def test_end_to_end__caching__interface_field_cacheable(graphql, undine_settings) -> None:
    class Named(InterfaceType, auto=False):
        name = InterfaceField(GraphQLNonNull(GraphQLString), cache_for_seconds=5)

    @Named
    class TaskType(QueryType[Task], auto=False): ...

    class Query(RootType):
        task = Entrypoint(TaskType, cache_for_seconds=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    assert TaskType.name.cache_for_seconds == 5
    assert TaskType.name.cache_per_user is False

    task = TaskFactory.create(name="Test task")

    query = """
        query($pk: Int!) {
          task(pk: $pk) {
            name
          }
        }
    """
    variables = {"pk": task.pk}

    with catch_cache_results() as results:
        response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.results == {"name": "Test task"}

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]

    key = get_cache_key(source=query, variables=variables)
    assert cache.get(key) is not None

    # Use more restrictive cache time from the field through the interface field
    assert results.cache_time == 5
    assert results.cache_per_user is False


@pytest.mark.django_db
def test_end_to_end__caching__interface_field_cacheable__entrypoint(graphql, undine_settings) -> None:
    class Named(InterfaceType, auto=False):
        name = InterfaceField(GraphQLNonNull(GraphQLString), cache_for_seconds=5)

    @Named
    class TaskType(QueryType[Task], auto=False):
        done = Field()

    @Named
    class ProjectType(QueryType[Project], auto=False): ...

    class Query(RootType):
        task = Entrypoint(TaskType)
        project = Entrypoint(ProjectType)
        named = Entrypoint(Named, cache_for_seconds=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Test task")

    query = """
        query {
          named {
            name
            ... on TaskType {
              done
            }
          }
        }
    """

    with catch_cache_results() as results:
        response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.results == [{"name": task.name, "done": task.done}]

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]

    key = get_cache_key(source=query, variables={})
    assert cache.get(key) is not None

    # Use more restrictive cache time from the field through the interface field
    assert results.cache_time == 5
    assert results.cache_per_user is False


@pytest.mark.django_db
def test_end_to_end__caching__interface_field_not_cacheable__entrypoint(graphql, undine_settings) -> None:
    class Named(InterfaceType, auto=False):
        name = InterfaceField(GraphQLNonNull(GraphQLString), cache_for_seconds=0)

    @Named
    class TaskType(QueryType[Task], auto=False):
        done = Field()

    @Named
    class ProjectType(QueryType[Project], auto=False): ...

    class Query(RootType):
        task = Entrypoint(TaskType)
        project = Entrypoint(ProjectType)
        named = Entrypoint(Named, cache_for_seconds=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Test task")

    query = """
        query {
          named {
            name
            ... on TaskType {
              done
            }
          }
        }
    """

    with catch_cache_results() as results:
        response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.results == [{"name": task.name, "done": task.done}]

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]

    key = get_cache_key(source=query, variables={})
    assert cache.get(key) is None

    # Use more restrictive cache time from the field through the interface field
    assert results.cache_time == 0
    assert results.cache_per_user is False


@pytest.mark.django_db
def test_end_to_end__caching__mutations_not_cacheable(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskCreateMutation(MutationType[Task], auto=True): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation, cache_for_seconds=10)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation($input: TaskCreateMutation!) {
          createTask(input: $input) {
            name
          }
        }
    """
    variables = {"input": {"name": "Test task", "type": "TASK"}}

    with catch_cache_results() as results:
        response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.results == {"name": "Test task"}

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]

    # Caching did not happen
    key = get_cache_key(source=query, variables=variables)
    assert cache.get(key) is None
    assert results.cache_time is Undefined
    assert results.cache_per_user is Undefined
