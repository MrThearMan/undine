from __future__ import annotations

from typing import Any

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Task, TaskStep
from tests.factories import TaskFactory, TaskStepFactory
from tests.helpers import keyset_cursor, walk_connection_forward_and_backward
from undine import Entrypoint, Field, GQLInfo, Order, OrderSet, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError
from undine.relay import Connection

NESTED_CONNECTION_QUERY = """
    query Tasks($first: Int, $after: String) {
      tasks {
        name
        steps(first: $first, after: $after) {
          totalCount
          pageInfo { hasNextPage hasPreviousPage startCursor endCursor }
          edges { cursor node { name } }
        }
      }
    }
"""


def create_nested_schema(*, page_size: int | None = None):
    class TaskStepType(QueryType[TaskStep], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(Connection(TaskStepType, page_size=page_size))

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    return create_schema(query=Query)


@pytest.mark.django_db
def test_nested_connection__per_parent(graphql, undine_settings) -> None:
    """Each parent row gets its own page, cursors, and 'totalCount'."""
    undine_settings.SCHEMA = create_nested_schema()

    task_1 = TaskFactory.create(name="Task 1")
    step_1 = TaskStepFactory.create(name="Step 1", task=task_1)
    step_2 = TaskStepFactory.create(name="Step 2", task=task_1)

    task_2 = TaskFactory.create(name="Task 2")
    step_3 = TaskStepFactory.create(name="Step 3", task=task_2)

    response = graphql(NESTED_CONNECTION_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "name": "Task 1",
                "steps": {
                    "totalCount": 2,
                    "pageInfo": {
                        "hasNextPage": False,
                        "hasPreviousPage": False,
                        "startCursor": keyset_cursor("TaskStepType", step_1.pk),
                        "endCursor": keyset_cursor("TaskStepType", step_2.pk),
                    },
                    "edges": [
                        {"cursor": keyset_cursor("TaskStepType", step_1.pk), "node": {"name": "Step 1"}},
                        {"cursor": keyset_cursor("TaskStepType", step_2.pk), "node": {"name": "Step 2"}},
                    ],
                },
            },
            {
                "name": "Task 2",
                "steps": {
                    "totalCount": 1,
                    "pageInfo": {
                        "hasNextPage": False,
                        "hasPreviousPage": False,
                        "startCursor": keyset_cursor("TaskStepType", step_3.pk),
                        "endCursor": keyset_cursor("TaskStepType", step_3.pk),
                    },
                    "edges": [
                        {"cursor": keyset_cursor("TaskStepType", step_3.pk), "node": {"name": "Step 3"}},
                    ],
                },
            },
        ],
    }


@pytest.mark.django_db
def test_nested_connection__empty(graphql, undine_settings) -> None:
    """A parent with no children still gets an empty connection instead of an error."""
    undine_settings.SCHEMA = create_nested_schema()

    TaskFactory.create(name="Task 1")

    response = graphql(NESTED_CONNECTION_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "name": "Task 1",
                "steps": {
                    "totalCount": 0,
                    "pageInfo": {
                        "hasNextPage": False,
                        "hasPreviousPage": False,
                        "startCursor": None,
                        "endCursor": None,
                    },
                    "edges": [],
                },
            },
        ],
    }


@pytest.mark.django_db
def test_nested_connection__first_and_after(graphql, undine_settings) -> None:
    """Paging arguments are applied inside each parent's own partition."""
    undine_settings.SCHEMA = create_nested_schema()

    task_1 = TaskFactory.create(name="Task 1")
    step_1 = TaskStepFactory.create(name="Step 1", task=task_1)
    step_2 = TaskStepFactory.create(name="Step 2", task=task_1)
    step_3 = TaskStepFactory.create(name="Step 3", task=task_1)

    response = graphql(NESTED_CONNECTION_QUERY, variables={"first": 2})
    assert response.has_errors is False, response.errors

    assert response.data["tasks"][0]["steps"] == {
        "totalCount": 3,
        "pageInfo": {
            "hasNextPage": True,
            "hasPreviousPage": False,
            "startCursor": keyset_cursor("TaskStepType", step_1.pk),
            "endCursor": keyset_cursor("TaskStepType", step_2.pk),
        },
        "edges": [
            {"cursor": keyset_cursor("TaskStepType", step_1.pk), "node": {"name": "Step 1"}},
            {"cursor": keyset_cursor("TaskStepType", step_2.pk), "node": {"name": "Step 2"}},
        ],
    }

    end_cursor = response.data["tasks"][0]["steps"]["pageInfo"]["endCursor"]

    response = graphql(NESTED_CONNECTION_QUERY, variables={"first": 2, "after": end_cursor})
    assert response.has_errors is False, response.errors

    assert response.data["tasks"][0]["steps"] == {
        "totalCount": 3,
        "pageInfo": {
            "hasNextPage": False,
            "hasPreviousPage": True,
            "startCursor": keyset_cursor("TaskStepType", step_3.pk),
            "endCursor": keyset_cursor("TaskStepType", step_3.pk),
        },
        "edges": [
            {"cursor": keyset_cursor("TaskStepType", step_3.pk), "node": {"name": "Step 3"}},
        ],
    }


@pytest.mark.django_db
def test_nested_connection__full_walk_forward_and_backward(graphql, undine_settings) -> None:
    """
    Paging forward with 'first' and backward with 'last' through a single parent's partition
    must both reproduce exactly the same order as an unpaginated query, with no skipped or
    duplicated row, and 'pageInfo' must be fully consistent on every page.
    """
    undine_settings.SCHEMA = create_nested_schema()

    task = TaskFactory.create(name="Task 1")
    TaskStepFactory.create(name="Step 1", task=task)
    TaskStepFactory.create(name="Step 2", task=task)
    TaskStepFactory.create(name="Step 3", task=task)
    TaskStepFactory.create(name="Step 4", task=task)
    TaskStepFactory.create(name="Step 5", task=task)

    query = """
        query Tasks($first: Int, $last: Int, $after: String, $before: String) {
          tasks {
            steps(first: $first, last: $last, after: $after, before: $before) {
              pageInfo { hasNextPage hasPreviousPage startCursor endCursor }
              edges { cursor node { name } }
            }
          }
        }
    """

    def edge_key(edge: dict) -> str:
        return edge["node"]["name"]

    def fetch_page(variables: dict) -> tuple[list[dict], dict]:
        response = graphql(query, variables=variables)
        assert response.has_errors is False, response.errors
        steps = response.data["tasks"][0]["steps"]
        return steps["edges"], steps["pageInfo"]

    full_edges, _ = fetch_page({})
    full_names = [edge_key(edge) for edge in full_edges]
    assert full_names == ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"]

    walk_connection_forward_and_backward(
        fetch_page=fetch_page,
        edge_key=edge_key,
        full_edges=full_names,
        page_size=2,
    )


@pytest.mark.django_db
def test_nested_connection__page_size(graphql, undine_settings) -> None:
    """The connection's own page size limits each parent's partition."""
    undine_settings.SCHEMA = create_nested_schema(page_size=1)

    task = TaskFactory.create(name="Task 1")
    step_1 = TaskStepFactory.create(name="Step 1", task=task)
    TaskStepFactory.create(name="Step 2", task=task)

    response = graphql(NESTED_CONNECTION_QUERY)
    assert response.has_errors is False, response.errors

    assert response.data["tasks"][0]["steps"] == {
        "totalCount": 2,
        "pageInfo": {
            "hasNextPage": True,
            "hasPreviousPage": False,
            "startCursor": keyset_cursor("TaskStepType", step_1.pk),
            "endCursor": keyset_cursor("TaskStepType", step_1.pk),
        },
        "edges": [
            {"cursor": keyset_cursor("TaskStepType", step_1.pk), "node": {"name": "Step 1"}},
        ],
    }


@pytest.mark.django_db
def test_nested_connection__alias(graphql, undine_settings) -> None:
    """An alias makes the optimizer prefetch to a separate attribute, which the resolver must still find."""
    undine_settings.SCHEMA = create_nested_schema()

    task = TaskFactory.create(name="Task 1")
    step = TaskStepFactory.create(name="Step 1", task=task)

    query = """
        query {
          tasks {
            originalSteps: steps {
              totalCount
              edges { cursor node { name } }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "originalSteps": {
                    "totalCount": 1,
                    "edges": [
                        {"cursor": keyset_cursor("TaskStepType", step.pk), "node": {"name": "Step 1"}},
                    ],
                },
            },
        ],
    }


# Stability


def create_nested_order_schema():
    class TaskStepOrderSet(OrderSet[TaskStep], auto=False):
        name = Order()

    class TaskStepType(QueryType[TaskStep], auto=False, orderset=TaskStepOrderSet):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(Connection(TaskStepType))

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    return create_schema(query=Query)


NESTED_CONNECTION_ORDER_QUERY = """
    query Tasks($first: Int, $after: String, $orderBy: [TaskStepOrderSet!]) {
      tasks {
        name
        steps(first: $first, after: $after, orderBy: $orderBy) {
          pageInfo { hasNextPage hasPreviousPage startCursor endCursor }
          edges { cursor node { name } }
        }
      }
    }
"""


@pytest.mark.django_db
def test_nested_connection__insert_before_cursor_does_not_duplicate(graphql, undine_settings) -> None:
    """Inserting a step that sorts before an already-fetched page does not shift or duplicate it."""
    undine_settings.SCHEMA = create_nested_order_schema()

    task = TaskFactory.create(name="Task 1")
    for name in ["b", "c", "d", "e"]:
        TaskStepFactory.create(name=name, task=task)

    response = graphql(NESTED_CONNECTION_ORDER_QUERY, variables={"first": 2, "orderBy": ["nameAsc"]})
    assert response.has_errors is False, response.errors
    assert [edge["node"]["name"] for edge in response.data["tasks"][0]["steps"]["edges"]] == ["b", "c"]

    cursor = response.data["tasks"][0]["steps"]["pageInfo"]["endCursor"]

    TaskStepFactory.create(name="a", task=task)

    response = graphql(
        NESTED_CONNECTION_ORDER_QUERY,
        variables={"first": 2, "after": cursor, "orderBy": ["nameAsc"]},
    )
    assert response.has_errors is False, response.errors
    assert [edge["node"]["name"] for edge in response.data["tasks"][0]["steps"]["edges"]] == ["d", "e"]


@pytest.mark.django_db
def test_nested_connection__delete_before_cursor_does_not_skip(graphql, undine_settings) -> None:
    """Deleting an already-fetched step does not shift the next page's boundary."""
    undine_settings.SCHEMA = create_nested_order_schema()

    task = TaskFactory.create(name="Task 1")
    for name in ["b", "c", "d", "e"]:
        TaskStepFactory.create(name=name, task=task)

    response = graphql(NESTED_CONNECTION_ORDER_QUERY, variables={"first": 2, "orderBy": ["nameAsc"]})
    assert response.has_errors is False, response.errors
    assert [edge["node"]["name"] for edge in response.data["tasks"][0]["steps"]["edges"]] == ["b", "c"]

    cursor = response.data["tasks"][0]["steps"]["pageInfo"]["endCursor"]

    TaskStep.objects.filter(name="b").delete()

    response = graphql(
        NESTED_CONNECTION_ORDER_QUERY,
        variables={"first": 2, "after": cursor, "orderBy": ["nameAsc"]},
    )
    assert response.has_errors is False, response.errors
    assert [edge["node"]["name"] for edge in response.data["tasks"][0]["steps"]["edges"]] == ["d", "e"]


@pytest.mark.django_db(transaction=True)
async def test_nested_connection__per_parent__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_nested_schema()

    task = await sync_to_async(TaskFactory.create)(name="Task 1")
    step_1 = await sync_to_async(TaskStepFactory.create)(name="Step 1", task=task)
    await sync_to_async(TaskStepFactory.create)(name="Step 2", task=task)

    response = await graphql_async(NESTED_CONNECTION_QUERY, variables={"first": 1})
    assert response.has_errors is False, response.errors

    assert response.data["tasks"][0]["steps"] == {
        "totalCount": 2,
        "pageInfo": {
            "hasNextPage": True,
            "hasPreviousPage": False,
            "startCursor": keyset_cursor("TaskStepType", step_1.pk),
            "endCursor": keyset_cursor("TaskStepType", step_1.pk),
        },
        "edges": [
            {"cursor": keyset_cursor("TaskStepType", step_1.pk), "node": {"name": "Step 1"}},
        ],
    }


# Permissions


@pytest.mark.django_db
def test_nested_connection__permissions__field(graphql, undine_settings) -> None:
    """A field permission hook denying access surfaces as a GraphQL error."""

    class TaskStepType(QueryType[TaskStep], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(Connection(TaskStepType))

        @steps.permissions
        def steps_permissions(self, info: GQLInfo, value: TaskStep) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task 1")
    TaskStepFactory.create(name="Step 1", task=task)

    response = graphql(NESTED_CONNECTION_QUERY)

    assert response.error_message(0) == "Permission denied."
    assert response.errors[0]["path"] == ["tasks", 0, "steps"]


@pytest.mark.django_db
def test_nested_connection__permissions__field__sees_instances(graphql, undine_settings) -> None:
    """A field permission hook is called for every instance in the page, and replaces '__permissions__'."""
    seen: list[Any] = []

    class TaskStepType(QueryType[TaskStep], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: TaskStep, info: GQLInfo) -> None:
            msg = "Should not be called."
            raise AssertionError(msg)

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(Connection(TaskStepType))

        @steps.permissions
        def steps_permissions(self, info: GQLInfo, value: TaskStep) -> None:
            seen.append(value)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task 1")
    step_1 = TaskStepFactory.create(name="Step 1", task=task)
    step_2 = TaskStepFactory.create(name="Step 2", task=task)

    response = graphql(NESTED_CONNECTION_QUERY)
    assert response.has_errors is False, response.errors

    assert seen == [step_1, step_2]
    assert response.data["tasks"][0]["steps"]["totalCount"] == 2


@pytest.mark.django_db
def test_nested_connection__permissions__query_type(graphql, undine_settings) -> None:
    """Without a field permission hook, the query type's '__permissions__' is checked for every instance."""

    class TaskStepType(QueryType[TaskStep], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: TaskStep, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(Connection(TaskStepType))

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task 1")
    TaskStepFactory.create(name="Step 1", task=task)

    response = graphql(NESTED_CONNECTION_QUERY)

    assert response.error_message(0) == "Permission denied."


@pytest.mark.django_db(transaction=True)
async def test_nested_connection__permissions__field__async(graphql_async, undine_settings) -> None:
    """A synchronous field permission hook is called as-is on the async path."""
    seen: list[Any] = []

    class TaskStepType(QueryType[TaskStep], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(Connection(TaskStepType))

        @steps.permissions
        def steps_permissions(self, info: GQLInfo, value: TaskStep) -> None:
            seen.append(value.name)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskStepFactory.create)(name="Step 1", task=task)

    response = await graphql_async(NESTED_CONNECTION_QUERY)
    assert response.has_errors is False, response.errors

    assert seen == ["Step 1"]


@pytest.mark.django_db(transaction=True)
async def test_nested_connection__permissions__field__async_hook(graphql_async, undine_settings) -> None:
    """An 'async def' field permission hook is awaited on the async path."""

    class TaskStepType(QueryType[TaskStep], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(Connection(TaskStepType))

        @steps.permissions
        async def steps_permissions(self, info: GQLInfo, value: TaskStep) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskStepFactory.create)(name="Step 1", task=task)

    response = await graphql_async(NESTED_CONNECTION_QUERY)

    assert response.error_message(0) == "Permission denied."


@pytest.mark.django_db(transaction=True)
async def test_nested_connection__permissions__query_type__async(graphql_async, undine_settings) -> None:
    """A synchronous '__permissions__' is called as-is on the async path."""

    class TaskStepType(QueryType[TaskStep], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: TaskStep, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(Connection(TaskStepType))

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskStepFactory.create)(name="Step 1", task=task)

    response = await graphql_async(NESTED_CONNECTION_QUERY)

    assert response.error_message(0) == "Permission denied."


@pytest.mark.django_db(transaction=True)
async def test_nested_connection__permissions__query_type__async_hook(graphql_async, undine_settings) -> None:
    """An 'async def __permissions__' is awaited on the async path."""

    class TaskStepType(QueryType[TaskStep], auto=False):
        name = Field()

        @classmethod
        async def __permissions__(cls, instance: TaskStep, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(Connection(TaskStepType))

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskStepFactory.create)(name="Step 1", task=task)

    response = await graphql_async(NESTED_CONNECTION_QUERY)

    assert response.error_message(0) == "Permission denied."
