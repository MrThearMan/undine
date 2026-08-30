from __future__ import annotations

from typing import Any

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import keyset_cursor, walk_connection_forward_and_backward
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError
from undine.relay import Connection, Node

CONNECTION_QUERY = """
    query Tasks($first: Int, $after: String) {
      tasks(first: $first, after: $after) {
        totalCount
        pageInfo { hasNextPage hasPreviousPage startCursor endCursor }
        edges { cursor node { name } }
      }
    }
"""


def create_task_schema():
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    return create_schema(query=Query)


@pytest.mark.django_db
def test_connection__empty(graphql, undine_settings) -> None:
    """With no rows, the connection has no edges and no cursors."""
    undine_settings.SCHEMA = create_task_schema()

    response = graphql(CONNECTION_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": {
            "totalCount": 0,
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": False,
                "startCursor": None,
                "endCursor": None,
            },
            "edges": [],
        },
    }


@pytest.mark.django_db
def test_connection__first_and_after(graphql, undine_settings) -> None:
    """Paging with 'first' and 'after' walks the whole connection, and 'totalCount' counts every row."""
    undine_settings.SCHEMA = create_task_schema()

    task_1 = TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")
    task_3 = TaskFactory.create(name="Task 3")

    response = graphql(CONNECTION_QUERY, variables={"first": 2})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": False,
                "startCursor": keyset_cursor("TaskType", task_1.pk),
                "endCursor": keyset_cursor("TaskType", task_2.pk),
            },
            "edges": [
                {"cursor": keyset_cursor("TaskType", task_1.pk), "node": {"name": "Task 1"}},
                {"cursor": keyset_cursor("TaskType", task_2.pk), "node": {"name": "Task 2"}},
            ],
        },
    }

    end_cursor = response.data["tasks"]["pageInfo"]["endCursor"]

    response = graphql(CONNECTION_QUERY, variables={"first": 2, "after": end_cursor})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": True,
                "startCursor": keyset_cursor("TaskType", task_3.pk),
                "endCursor": keyset_cursor("TaskType", task_3.pk),
            },
            "edges": [
                {"cursor": keyset_cursor("TaskType", task_3.pk), "node": {"name": "Task 3"}},
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
async def test_connection__first_and_after__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_task_schema()

    task_1 = await sync_to_async(TaskFactory.create)(name="Task 1")
    task_2 = await sync_to_async(TaskFactory.create)(name="Task 2")

    response = await graphql_async(CONNECTION_QUERY, variables={"first": 1})
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": {
            "totalCount": 2,
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": False,
                "startCursor": keyset_cursor("TaskType", task_1.pk),
                "endCursor": keyset_cursor("TaskType", task_1.pk),
            },
            "edges": [
                {"cursor": keyset_cursor("TaskType", task_1.pk), "node": {"name": "Task 1"}},
            ],
        },
    }

    end_cursor = response.data["tasks"]["pageInfo"]["endCursor"]

    response = await graphql_async(CONNECTION_QUERY, variables={"first": 1, "after": end_cursor})
    assert response.has_errors is False, response.errors

    assert response.data["tasks"]["edges"] == [
        {"cursor": keyset_cursor("TaskType", task_2.pk), "node": {"name": "Task 2"}},
    ]


@pytest.mark.django_db
def test_connection__full_walk_forward_and_backward(graphql, undine_settings) -> None:
    """
    Paging forward with 'first' and backward with 'last' must both reproduce exactly the same
    order as an unpaginated query, with no skipped or duplicated row, and 'pageInfo' must be
    fully consistent on every page.
    """
    undine_settings.SCHEMA = create_task_schema()

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")
    TaskFactory.create(name="Task 4")
    TaskFactory.create(name="Task 5")

    query = """
        query Tasks($first: Int, $last: Int, $after: String, $before: String) {
          tasks(first: $first, last: $last, after: $after, before: $before) {
            pageInfo { hasNextPage hasPreviousPage startCursor endCursor }
            edges { cursor node { name } }
          }
        }
    """

    def edge_key(edge: dict) -> str:
        return edge["node"]["name"]

    def fetch_page(variables: dict) -> tuple[list[dict], dict]:
        response = graphql(query, variables=variables)
        assert response.has_errors is False, response.errors
        return response.data["tasks"]["edges"], response.data["tasks"]["pageInfo"]

    full_edges, _ = fetch_page({})
    full_names = [edge_key(edge) for edge in full_edges]
    assert full_names == ["Task 1", "Task 2", "Task 3", "Task 4", "Task 5"]

    walk_connection_forward_and_backward(
        fetch_page=fetch_page,
        edge_key=edge_key,
        full_edges=full_names,
        page_size=2,
    )


# Permissions


@pytest.mark.django_db
def test_connection__permissions__query_type(graphql, undine_settings) -> None:
    """'__permissions__' on the query type is checked for every instance in the page."""

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")

    response = graphql(CONNECTION_QUERY)

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
def test_connection__permissions__entrypoint(graphql, undine_settings) -> None:
    """An entrypoint permission hook replaces '__permissions__' and sees every instance in the page."""
    seen: list[Any] = []

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            msg = "Should not be called."
            raise AssertionError(msg)

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

        @tasks.permissions
        def tasks_permissions(self, info: GQLInfo, value: Task) -> None:
            seen.append(value)

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")

    response = graphql(CONNECTION_QUERY)
    assert response.has_errors is False, response.errors

    assert seen == [task_1, task_2]
    assert response.data["tasks"]["totalCount"] == 2


@pytest.mark.django_db(transaction=True)
async def test_connection__permissions__query_type__async(graphql_async, undine_settings) -> None:
    """A synchronous '__permissions__' is called as-is on the async path."""

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(CONNECTION_QUERY)

    assert response.error_message(0) == "Permission denied."


@pytest.mark.django_db(transaction=True)
async def test_connection__permissions__query_type__async_hook(graphql_async, undine_settings) -> None:
    """An 'async def __permissions__' is awaited on the async path."""

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(CONNECTION_QUERY)

    assert response.error_message(0) == "Permission denied."


@pytest.mark.django_db(transaction=True)
async def test_connection__permissions__entrypoint__async(graphql_async, undine_settings) -> None:
    """A synchronous entrypoint permission hook is called as-is on the async path."""
    seen: list[Any] = []

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

        @tasks.permissions
        def tasks_permissions(self, info: GQLInfo, value: Task) -> None:
            seen.append(value.name)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(CONNECTION_QUERY)
    assert response.has_errors is False, response.errors

    assert seen == ["Task 1"]


@pytest.mark.django_db(transaction=True)
async def test_connection__permissions__entrypoint__async_hook(graphql_async, undine_settings) -> None:
    """An 'async def' entrypoint permission hook is awaited on the async path."""

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(Connection(TaskType))

        @tasks.permissions
        async def tasks_permissions(self, info: GQLInfo, value: Task) -> None:
            raise GraphQLPermissionError

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async(CONNECTION_QUERY)

    assert response.error_message(0) == "Permission denied."
