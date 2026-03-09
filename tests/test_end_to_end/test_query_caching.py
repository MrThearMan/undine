from __future__ import annotations

import dataclasses
import hashlib
import json
from contextlib import contextmanager
from typing import Any, Generator
from unittest.mock import patch

import freezegun
import pytest
from django.core.cache import caches
from django.core.cache.backends.locmem import LocMemCache
from graphql import GraphQLNonNull, GraphQLString, Undefined

from example_project.app.models import Project, Task
from tests.factories import ProjectFactory, TaskFactory, UserFactory
from undine import (
    Entrypoint,
    Field,
    InterfaceField,
    InterfaceType,
    MutationType,
    QueryType,
    RootType,
    create_schema,
    settings,
)
from undine.dataclasses import CacheControlResults
from undine.exceptions import GraphQLPermissionError
from undine.hooks import LifecycleHookContext
from undine.typing import CacheKeyData, GQLInfo
from undine.utils.graphql.caching import RequestCacheCalculator


@pytest.fixture(autouse=True)
def _clear_sse_cache(undine_settings):
    """Handle clearing the cache between runs so that cache data is not shared between tests."""
    yield
    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]
    cache.clear()


def get_cache_key(
    *,
    source: str,
    variables: dict[str, Any],
    operation_name: str | None = None,
    is_authenticated: bool = False,
    user_id: int | None = Undefined,
    extra_context: dict[str, Any] | None = None,
) -> str:
    key_data = CacheKeyData(
        source=source,
        variables=json.dumps(variables, separators=(",", ":"), sort_keys=True),
        operation_name=operation_name,
        extensions="{}",
        is_authenticated=is_authenticated,
    )
    if user_id is not Undefined:
        key_data["user_pk"] = user_id

    if extra_context:
        key_data["extra"] = json.dumps(extra_context, separators=(",", ":"), sort_keys=True)

    key = hashlib.sha256(json.dumps(key_data, separators=(",", ":")).encode()).hexdigest()
    return f"{settings.undine_settings.REQUEST_CACHE_PREFIX}:{key}"


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


@dataclasses.dataclass
class CacheIOResults:
    reads: int = dataclasses.field(default=0)
    writes: int = dataclasses.field(default=0)


@contextmanager
def record_cache_reads_and_writes() -> Generator[CacheIOResults, None, None]:
    original_get = LocMemCache.get
    original_set = LocMemCache.set

    def mock_get(*args, **kwargs):
        value = original_get(*args, **kwargs)
        if value is not None:
            results.reads += 1
        return value

    def mock_set(*args, **kwargs):
        results.writes += 1
        return original_set(*args, **kwargs)

    results = CacheIOResults()

    with (
        patch.object(LocMemCache, "get", new=mock_get),
        patch.object(LocMemCache, "set", new=mock_set),
    ):
        yield results


@pytest.mark.django_db
def test_end_to_end__caching__entrypoint_cacheable(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

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

    user = UserFactory.create()
    graphql.force_login(user=user)

    with catch_cache_results() as results:
        response = graphql(query, variables=variables)

    assert response.has_errors is False, response.errors
    assert response.results == {"name": "Test task"}

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]

    key = get_cache_key(source=query, variables=variables, is_authenticated=True)
    assert cache.get(key) is not None

    # Unauthenticated users have different cache
    key = get_cache_key(source=query, variables=variables)
    assert cache.get(key) is None

    assert results.cache_time == 10
    assert results.cache_per_user is False

    assert response.response.headers["Cache-Control"] == "max-age=10"
    assert response.response.headers["Age"] == "0"


@pytest.mark.django_db
def test_end_to_end__caching__entrypoint_cacheable__anonymous(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

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

    # Authenticated users have different cache
    key = get_cache_key(source=query, variables=variables, is_authenticated=True)
    assert cache.get(key) is None

    assert results.cache_time == 10
    assert results.cache_per_user is False

    assert response.response.headers["Cache-Control"] == "max-age=10"
    assert response.response.headers["Age"] == "0"


@pytest.mark.django_db
def test_end_to_end__caching__entrypoint_cacheable__per_user(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10, cache_per_user=True)

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

    key_user = get_cache_key(source=query, variables=variables, user_id=user_1.pk, is_authenticated=True)
    assert cache.get(key_user) is not None

    # Not cached for user 2
    key_user = get_cache_key(source=query, variables=variables, user_id=user_2.pk, is_authenticated=True)
    assert cache.get(key_user) is None

    # Not cached for anonymous user.
    key_user = get_cache_key(source=query, variables=variables, user_id=None, is_authenticated=True)
    assert cache.get(key_user) is None

    assert results.cache_time == 10
    assert results.cache_per_user is True

    assert response.response.headers["Cache-Control"] == "max-age=10, private"
    assert response.response.headers["Age"] == "0"


@pytest.mark.django_db
def test_end_to_end__caching__entrypoint_cacheable__per_user__anonymous(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10, cache_per_user=True)

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

    # Not cached as public response
    key_all = get_cache_key(source=query, variables=variables)
    assert cache.get(key_all) is None

    key_user = get_cache_key(source=query, variables=variables, user_id=None)
    assert cache.get(key_user) is not None

    assert response.response.headers["Cache-Control"] == "max-age=10, private"
    assert response.response.headers["Age"] == "0"


@pytest.mark.django_db
def test_end_to_end__caching__entrypoint_cacheable__cache_write_and_read(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

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

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]
    key = get_cache_key(source=query, variables=variables)

    with freezegun.freeze_time("2023-01-01T10:00:00Z") as freezer:
        with record_cache_reads_and_writes() as results:
            response = graphql(query, variables=variables)

        assert response.has_errors is False, response.errors
        assert cache.get(key) is not None

        assert results.reads == 0
        assert results.writes == 1

        assert response.response.headers["Cache-Control"] == "max-age=10"
        assert response.response.headers["Age"] == "0"

        freezer.move_to("2023-01-01T10:00:05Z")

        with record_cache_reads_and_writes() as results:
            response = graphql(query, variables=variables)

        assert response.has_errors is False, response.errors
        assert cache.get(key) is not None

        assert results.reads == 1
        assert results.writes == 0

        assert response.response.headers["Cache-Control"] == "max-age=10"
        assert response.response.headers["Age"] == "5"


@pytest.mark.django_db
def test_end_to_end__caching__entrypoint_cacheable__extra_context(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

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

    # Example: Use extra context to cache separately for different languages
    def extra_context(context: LifecycleHookContext) -> dict[str, Any]:
        return {"lang": context.request.headers.get("Accept-Language", "en")}

    undine_settings.REQUEST_CACHE_EXTRA_CONTEXT = extra_context

    headers = {"Accept-Language": "fi"}

    response = graphql(query, variables=variables, headers=headers)
    assert response.has_errors is False, response.errors

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]

    key = get_cache_key(source=query, variables=variables, extra_context={"lang": "fi"})
    assert cache.get(key) is not None

    # Other languages have different cache
    key = get_cache_key(source=query, variables=variables, extra_context={"lang": "en"})
    assert cache.get(key) is None


@pytest.mark.django_db
def test_end_to_end__caching__entrypoint_cacheable__should_read_from_cache(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

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

    # Example: Only read from cache for requests for a specific language
    def should_read_from_cache(context: LifecycleHookContext) -> bool:
        return context.request.headers.get("Accept-Language") == "fi"

    undine_settings.REQUEST_CACHE_READ_PREDICATE = should_read_from_cache

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]
    key = get_cache_key(source=query, variables=variables)

    with record_cache_reads_and_writes() as results:
        response = graphql(query, variables=variables, headers={"Accept-Language": "en"})

    assert response.has_errors is False, response.errors
    assert cache.get(key) is not None

    # Nothing to read yet
    assert results.reads == 0
    assert results.writes == 1

    with record_cache_reads_and_writes() as results:
        response = graphql(query, variables=variables, headers={"Accept-Language": "en"})

    assert response.has_errors is False, response.errors

    # We don't read due to the predicate
    assert results.reads == 0
    assert results.writes == 1


@pytest.mark.django_db
def test_end_to_end__caching__entrypoint_cacheable__should_write_to_cache(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

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

    # Example: Only write to cache for requests for a specific language
    def should_write_to_cache(context: LifecycleHookContext) -> bool:
        return context.request.headers.get("Accept-Language") == "fi"

    undine_settings.REQUEST_CACHE_WRITE_PREDICATE = should_write_to_cache

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]
    key = get_cache_key(source=query, variables=variables)

    with record_cache_reads_and_writes() as results:
        response = graphql(query, variables=variables, headers={"Accept-Language": "en"})

    assert response.has_errors is False, response.errors
    assert cache.get(key) is None

    assert results.reads == 0
    assert results.writes == 0


@pytest.mark.django_db
def test_end_to_end__caching__entrypoint_cacheable__dont_cache_errors(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

        @task.permissions
        def task_permissions(self: TaskType, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

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

    with record_cache_reads_and_writes() as results:
        response = graphql(query, variables=variables)

    assert response.has_errors is True
    assert response.errors[0]["message"] == "Permission denied."

    cache = caches[undine_settings.REQUEST_CACHE_ALIAS]

    key = get_cache_key(source=query, variables=variables)
    assert cache.get(key) is None

    assert results.reads == 0
    assert results.writes == 0

    assert "Cache-Control" not in response.response.headers
    assert "Age" not in response.response.headers


@pytest.mark.django_db
def test_end_to_end__caching__entrypoint_not_cacheable__field_ignored(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field(cache_time=10)

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
    class TaskType(QueryType[Task], auto=False, cache_time=10):
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
        name = Field(cache_time=5)

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

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
        name = Field(cache_time=0)

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

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
    class ProjectType(QueryType[Project], auto=False, cache_time=0):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

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
        name = InterfaceField(GraphQLNonNull(GraphQLString), cache_time=5)

    @Named
    class TaskType(QueryType[Task], auto=False): ...

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    assert TaskType.name.cache_time == 5
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
        name = InterfaceField(GraphQLNonNull(GraphQLString), cache_time=5)

    @Named
    class TaskType(QueryType[Task], auto=False):
        done = Field()

    @Named
    class ProjectType(QueryType[Project], auto=False): ...

    class Query(RootType):
        task = Entrypoint(TaskType)
        project = Entrypoint(ProjectType)
        named = Entrypoint(Named, cache_time=10)

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
        name = InterfaceField(GraphQLNonNull(GraphQLString), cache_time=0)

    @Named
    class TaskType(QueryType[Task], auto=False):
        done = Field()

    @Named
    class ProjectType(QueryType[Project], auto=False): ...

    class Query(RootType):
        task = Entrypoint(TaskType)
        project = Entrypoint(ProjectType)
        named = Entrypoint(Named, cache_time=10)

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
        create_task = Entrypoint(TaskCreateMutation, cache_time=10)

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
