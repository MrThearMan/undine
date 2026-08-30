from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError

if TYPE_CHECKING:
    from django.db.models import QuerySet

QUERY = """
    query Tasks {
      tasks {
        name
      }
    }
"""


@pytest.mark.django_db
def test_query_many__multiple_rows(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")

    response = graphql(QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1"}, {"name": "Task 2"}]}


@pytest.mark.django_db(transaction=True)
async def test_query_many__multiple_rows__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")

    response = await graphql_async(QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1"}, {"name": "Task 2"}]}


@pytest.mark.django_db
def test_query_many__no_rows(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql(QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": []}


@pytest.mark.django_db(transaction=True)
async def test_query_many__no_rows__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    response = await graphql_async(QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": []}


@pytest.mark.django_db
def test_query_many__filter_queryset(graphql, undine_settings) -> None:
    """'__filter_queryset__' narrows what the entrypoint returns."""

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __filter_queryset__(cls, queryset: QuerySet[Task], info: GQLInfo) -> QuerySet[Task]:
            return queryset.filter(name="Task 1")

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")

    response = graphql(QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1"}]}


@pytest.mark.django_db(transaction=True)
async def test_query_many__filter_queryset__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __filter_queryset__(cls, queryset: QuerySet[Task], info: GQLInfo) -> QuerySet[Task]:
            return queryset.filter(name="Task 1")

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")

    response = await graphql_async(QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1"}]}


@pytest.mark.django_db
def test_query_many__query_type_permissions(graphql, undine_settings) -> None:
    """'__permissions__' is checked for every row in the result."""
    checked: list[str] = []

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            checked.append(instance.name)
            if instance.name == "Task 2":
                raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")

    response = graphql(QUERY)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["tasks"],
            },
        ],
    }

    assert checked == ["Task 1", "Task 2"]


@pytest.mark.django_db(transaction=True)
async def test_query_many__query_type_permissions__async(graphql_async, undine_settings) -> None:
    """A synchronous '__permissions__' hook is called directly on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(QUERY)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["tasks"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_query_many__query_type_permissions__async_hook(graphql_async, undine_settings) -> None:
    """An asynchronous '__permissions__' hook is awaited on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(QUERY)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["tasks"],
            },
        ],
    }


@pytest.mark.django_db
def test_query_many__entrypoint_permissions(graphql, undine_settings) -> None:
    """An entrypoint permissions function takes precedence over '__permissions__'."""
    checked: list[str] = []

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            msg = "Should not be called"
            raise RuntimeError(msg)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

        @tasks.permissions
        def tasks_permissions(self, info: GQLInfo, value: Task) -> None:
            checked.append(value.name)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")

    response = graphql(QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1"}, {"name": "Task 2"}]}
    assert checked == ["Task 1", "Task 2"]


@pytest.mark.django_db(transaction=True)
async def test_query_many__entrypoint_permissions__async(graphql_async, undine_settings) -> None:
    """A synchronous entrypoint permissions function is called directly on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

        @tasks.permissions
        def tasks_permissions(self, info: GQLInfo, value: Task) -> None:
            if value.name != "Task 1":
                raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 2")

    response = await graphql_async(QUERY)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["tasks"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_query_many__entrypoint_permissions__async_func(graphql_async, undine_settings) -> None:
    """An asynchronous entrypoint permissions function is awaited on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

        @tasks.permissions
        async def tasks_permissions(self, info: GQLInfo, value: Task) -> None:
            if value.name != "Task 1":
                raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 2")

    response = await graphql_async(QUERY)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["tasks"],
            },
        ],
    }
