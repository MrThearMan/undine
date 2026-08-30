from __future__ import annotations

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError
from undine.utils.text import dotpath

QUERY = """
    query Task($pk: Int!) {
      task(pk: $pk) {
        name
      }
    }
"""


@pytest.mark.django_db
def test_query_single__by_pk(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")

    response = graphql(QUERY, variables={"pk": task.pk})
    assert response.has_errors is False, response.errors

    assert response.data == {"task": {"name": "Task 1"}}


@pytest.mark.django_db(transaction=True)
async def test_query_single__by_pk__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")

    response = await graphql_async(QUERY, variables={"pk": task.pk})
    assert response.has_errors is False, response.errors

    assert response.data == {"task": {"name": "Task 1"}}


@pytest.mark.django_db
def test_query_single__not_found__nullable(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql(QUERY, variables={"pk": 1})
    assert response.has_errors is False, response.errors

    assert response.data == {"task": None}


@pytest.mark.django_db(transaction=True)
async def test_query_single__not_found__nullable__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    response = await graphql_async(QUERY, variables={"pk": 1})
    assert response.has_errors is False, response.errors

    assert response.data == {"task": None}


@pytest.mark.django_db
def test_query_single__not_found__not_nullable(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=False)

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql(QUERY, variables={"pk": 1})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": f"Primary key 1 on model '{dotpath(TaskType)}' did not match any row.",
                "extensions": {
                    "status_code": 404,
                    "error_code": "MODEL_INSTANCE_NOT_FOUND",
                },
                "path": ["task"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_query_single__not_found__not_nullable__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=False)

    undine_settings.SCHEMA = create_schema(query=Query)

    response = await graphql_async(QUERY, variables={"pk": 1})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": f"Primary key 1 on model '{dotpath(TaskType)}' did not match any row.",
                "extensions": {
                    "status_code": 404,
                    "error_code": "MODEL_INSTANCE_NOT_FOUND",
                },
                "path": ["task"],
            },
        ],
    }


@pytest.mark.django_db
def test_query_single__query_type_permissions(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task 1")

    response = graphql(QUERY, variables={"pk": task.pk})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["task"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_query_single__query_type_permissions__async(graphql_async, undine_settings) -> None:
    """A synchronous '__permissions__' hook is called directly on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(QUERY, variables={"pk": task.pk})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["task"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_query_single__query_type_permissions__async_hook(graphql_async, undine_settings) -> None:
    """An asynchronous '__permissions__' hook is awaited on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(QUERY, variables={"pk": task.pk})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["task"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_query_single__entrypoint_permissions__async(graphql_async, undine_settings) -> None:
    """A synchronous entrypoint permissions function is called directly on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

        @task.permissions
        def task_permissions(self, info: GQLInfo, value: Task) -> None:
            if value.name != "Task 1":
                raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Task 2")

    response = await graphql_async(QUERY, variables={"pk": task.pk})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["task"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_query_single__entrypoint_permissions__async_func(graphql_async, undine_settings) -> None:
    """An asynchronous entrypoint permissions function is awaited on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

        @task.permissions
        async def task_permissions(self, info: GQLInfo, value: Task) -> None:
            if value.name != "Task 1":
                raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Task 2")

    response = await graphql_async(QUERY, variables={"pk": task.pk})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["task"],
            },
        ],
    }
