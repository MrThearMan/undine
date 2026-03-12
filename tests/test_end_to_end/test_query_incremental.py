from __future__ import annotations

import asyncio
import operator
from typing import AsyncIterator

import pytest
from asgiref.sync import sync_to_async
from graphql import GraphQLError, version_info

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError
from undine.optimizer import OptimizationData

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(version_info < (3, 3, 0), reason="requires graphql >= 3.3.0"),
]


# Defer directive


async def test_end_to_end__defer(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        async def slow(self: Task) -> str:
            return "slow"

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="foo", points=1)
    await sync_to_async(TaskFactory.create)(name="bar", points=2)
    await sync_to_async(TaskFactory.create)(name="baz", points=3)

    query = """
        query {
          tasks {
            name
            ... @defer {
              slow
            }
          }
        }
    """

    responses = [response.json async for response in graphql_async.incremental_delivery(query)]

    assert len(responses) == 2

    assert responses[0] == {
        "hasNext": True,
        "data": {
            "tasks": [
                {"name": "foo"},
                {"name": "bar"},
                {"name": "baz"},
            ],
        },
        "pending": [
            {"id": "0", "path": ["tasks", 0]},
            {"id": "1", "path": ["tasks", 1]},
            {"id": "2", "path": ["tasks", 2]},
        ],
    }

    assert responses[1] == {
        "hasNext": False,
        "incremental": [
            {"id": "0", "data": {"slow": "slow"}},
            {"id": "1", "data": {"slow": "slow"}},
            {"id": "2", "data": {"slow": "slow"}},
        ],
        "completed": [
            {"id": "0"},
            {"id": "1"},
            {"id": "2"},
        ],
    }


async def test_end_to_end__defer__multiple_subsequent_responses(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        async def slow(self: Task) -> str:
            await asyncio.sleep(self.points * 0.1)
            return "slow"

        @slow.optimize
        def slow_optimized(self, data: OptimizationData, info: GQLInfo) -> None:
            return data.only_fields.add("points")

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="foo", points=1)
    await sync_to_async(TaskFactory.create)(name="bar", points=2)
    await sync_to_async(TaskFactory.create)(name="baz", points=3)

    query = """
        query {
          tasks {
            name
            ... @defer {
              slow
            }
          }
        }
    """

    responses = [response.json async for response in graphql_async.incremental_delivery(query)]

    assert len(responses) == 4

    assert responses[0] == {
        "hasNext": True,
        "data": {
            "tasks": [
                {"name": "foo"},
                {"name": "bar"},
                {"name": "baz"},
            ],
        },
        "pending": [
            {"id": "0", "path": ["tasks", 0]},
            {"id": "1", "path": ["tasks", 1]},
            {"id": "2", "path": ["tasks", 2]},
        ],
    }

    assert responses[1] == {
        "hasNext": True,
        "completed": [{"id": "0"}],
        "incremental": [
            {"id": "0", "data": {"slow": "slow"}},
        ],
    }

    assert responses[2] == {
        "hasNext": True,
        "completed": [{"id": "1"}],
        "incremental": [
            {"id": "1", "data": {"slow": "slow"}},
        ],
    }

    assert responses[3] == {
        "hasNext": False,
        "completed": [{"id": "2"}],
        "incremental": [
            {"id": "2", "data": {"slow": "slow"}},
        ],
    }


async def test_end_to_end__defer__errors_in_initial_responses(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @name.permissions
        def name_permissions(self: Task, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

        @Field
        async def slow(self: Task) -> str:
            return "slow"

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="foo", points=1)
    await sync_to_async(TaskFactory.create)(name="bar", points=2)
    await sync_to_async(TaskFactory.create)(name="baz", points=3)

    query = """
        query {
          tasks {
            name
            ... @defer {
              slow
            }
          }
        }
    """

    responses = [response.json async for response in graphql_async.incremental_delivery(query)]

    assert len(responses) == 1

    assert responses[0] == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "path": ["tasks", 0, "name"],
                "extensions": {"error_code": "PERMISSION_DENIED", "status_code": 403},
            }
        ],
        "hasNext": False,
        "pending": [],
    }


async def test_end_to_end__defer__errors_in_subsequent_responses(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        async def slow(self: Task) -> str:
            sleep_time = self.points * 0.1

            if sleep_time > 0.2:
                msg = "dont even try"
                raise GraphQLError(msg)

            await asyncio.sleep(sleep_time)

            if sleep_time > 0.1:
                msg = "too slow"
                raise GraphQLError(msg)

            return "slow"

        @slow.optimize
        def slow_optimized(self, data: OptimizationData, info: GQLInfo) -> None:
            return data.only_fields.add("points")

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="foo", points=1)
    await sync_to_async(TaskFactory.create)(name="bar", points=2)
    await sync_to_async(TaskFactory.create)(name="baz", points=3)

    query = """
        query {
          tasks {
            name
            ... @defer {
              slow
            }
          }
        }
    """

    responses = [response.json async for response in graphql_async.incremental_delivery(query)]

    assert len(responses) == 4

    assert responses[0] == {
        "hasNext": True,
        "data": {
            "tasks": [
                {"name": "foo"},
                {"name": "bar"},
                {"name": "baz"},
            ],
        },
        "pending": [
            {"id": "0", "path": ["tasks", 0]},
            {"id": "1", "path": ["tasks", 1]},
            {"id": "2", "path": ["tasks", 2]},
        ],
    }

    assert responses[1] == {
        "hasNext": True,
        "completed": [
            {
                "id": "2",
                "errors": [
                    {
                        "message": "dont even try",
                        "path": ["tasks", 2, "slow"],
                        "extensions": {"status_code": 400},
                    }
                ],
            }
        ],
    }

    assert responses[2] == {
        "hasNext": True,
        "completed": [{"id": "0"}],
        "incremental": [
            {"id": "0", "data": {"slow": "slow"}},
        ],
    }

    assert responses[3] == {
        "hasNext": False,
        "completed": [
            {
                "id": "1",
                "errors": [
                    {
                        "message": "too slow",
                        "path": ["tasks", 1, "slow"],
                        "extensions": {"status_code": 400},
                    },
                ],
            }
        ],
    }


# Stram directive


async def test_end_to_end__stream(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        async def slow(self: Task) -> list[str]:
            return ["slow"]

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="foo", points=1)
    await sync_to_async(TaskFactory.create)(name="bar", points=2)
    await sync_to_async(TaskFactory.create)(name="baz", points=3)

    query = """
        query {
          tasks {
            name
            slow @stream
          }
        }
    """

    responses = [response.json async for response in graphql_async.incremental_delivery(query)]

    assert len(responses) == 2

    assert responses[0] == {
        "hasNext": True,
        "data": {
            "tasks": [
                {"name": "foo", "slow": []},
                {"name": "bar", "slow": []},
                {"name": "baz", "slow": []},
            ],
        },
        "pending": [
            {"id": "0", "path": ["tasks", 0, "slow"]},
            {"id": "1", "path": ["tasks", 1, "slow"]},
            {"id": "2", "path": ["tasks", 2, "slow"]},
        ],
    }

    assert responses[1] == {
        "hasNext": False,
        "completed": [
            {"id": "0"},
            {"id": "1"},
            {"id": "2"},
        ],
        "incremental": [
            {"id": "0", "items": ["slow"]},
            {"id": "1", "items": ["slow"]},
            {"id": "2", "items": ["slow"]},
        ],
    }


async def test_end_to_end__stream__multiple_subsequent_responses(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        async def slow(self: Task) -> AsyncIterator[str]:
            for _ in range(self.points):
                await asyncio.sleep(0.1)
                yield "slow"

        @slow.optimize
        def slow_optimized(self: Field, data: OptimizationData, info: GQLInfo) -> None:
            return data.only_fields.add("points")

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="foo", points=1)
    await sync_to_async(TaskFactory.create)(name="bar", points=2)
    await sync_to_async(TaskFactory.create)(name="baz", points=3)

    query = """
        query {
          tasks {
            name
            slow @stream
          }
        }
    """

    responses = [response.json async for response in graphql_async.incremental_delivery(query)]

    # Compare like this to ensure deferred field resolution order doesnt matter for asserts
    assert len(responses) == 4

    assert sorted(responses[0]) == ["data", "hasNext", "pending"]
    assert responses[0]["hasNext"] is True
    assert responses[0]["data"] == {
        "tasks": [
            {"name": "foo", "slow": []},
            {"name": "bar", "slow": []},
            {"name": "baz", "slow": []},
        ],
    }
    assert sorted(responses[0]["pending"], key=operator.itemgetter("id")) == [
        {"id": "0", "path": ["tasks", 0, "slow"]},
        {"id": "1", "path": ["tasks", 1, "slow"]},
        {"id": "2", "path": ["tasks", 2, "slow"]},
    ]

    assert sorted(responses[1]) == ["completed", "hasNext", "incremental"]
    assert responses[1]["hasNext"] is True
    assert responses[1]["completed"] == [{"id": "0"}]
    assert sorted(responses[1]["incremental"], key=operator.itemgetter("id")) == [
        {"id": "0", "items": ["slow"]},
        {"id": "1", "items": ["slow"]},
        {"id": "2", "items": ["slow"]},
    ]

    assert sorted(responses[2]) == ["completed", "hasNext", "incremental"]
    assert responses[2]["hasNext"] is True
    assert responses[2]["completed"] == [{"id": "1"}]
    assert sorted(responses[2]["incremental"], key=operator.itemgetter("id")) == [
        {"id": "1", "items": ["slow"]},
        {"id": "2", "items": ["slow"]},
    ]

    assert sorted(responses[3]) == ["completed", "hasNext", "incremental"]
    assert responses[3]["hasNext"] is False
    assert responses[3]["completed"] == [{"id": "2"}]
    assert responses[3]["incremental"] == [
        {"id": "2", "items": ["slow"]},
    ]


async def test_end_to_end__stream__errors_in_initial_response(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        async def slow(self: Task) -> list[str]:
            return ["slow"]

        @slow.permissions
        def slow_permissions(self: Task, info: GQLInfo, value: list[str]) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="foo", points=1)
    await sync_to_async(TaskFactory.create)(name="bar", points=2)
    await sync_to_async(TaskFactory.create)(name="baz", points=3)

    query = """
        query {
          tasks {
            name
            slow @stream
          }
        }
    """

    response = [response.json async for response in graphql_async.incremental_delivery(query)]

    assert len(response) == 1

    assert response[0] == {
        "hasNext": False,
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "path": ["tasks", 0, "slow"],
                "extensions": {"error_code": "PERMISSION_DENIED", "status_code": 403},
            }
        ],
        "pending": [],
    }


async def test_end_to_end__stream__errors_in_subsequent_responses(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        async def slow(self: Task) -> AsyncIterator[str]:
            if self.points == 1:
                msg = "dont even try"
                raise GraphQLError(msg)

            for i in range(self.points):
                if i == 2:
                    msg = "too slow"
                    raise GraphQLError(msg)

                await asyncio.sleep(0.1)
                yield "slow"

        @slow.optimize
        def slow_optimized(self: Field, data: OptimizationData, info: GQLInfo) -> None:
            return data.only_fields.add("points")

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="foo", points=1)
    await sync_to_async(TaskFactory.create)(name="bar", points=2)
    await sync_to_async(TaskFactory.create)(name="baz", points=3)

    query = """
        query {
          tasks {
            name
            slow @stream
          }
        }
    """

    responses = [response.json async for response in graphql_async.incremental_delivery(query)]

    assert len(responses) == 4

    assert responses[0] == {
        "hasNext": True,
        "data": {
            "tasks": [
                {"name": "foo", "slow": []},
                {"name": "bar", "slow": []},
                {"name": "baz", "slow": []},
            ],
        },
        "pending": [
            {"id": "0", "path": ["tasks", 0, "slow"]},
            {"id": "1", "path": ["tasks", 1, "slow"]},
            {"id": "2", "path": ["tasks", 2, "slow"]},
        ],
    }

    assert responses[1] == {
        "hasNext": True,
        "completed": [
            {
                "id": "0",
                "errors": [
                    {
                        "message": "dont even try",
                        "path": ["tasks", 0, "slow"],
                        "extensions": {"status_code": 400},
                    }
                ],
            }
        ],
    }

    assert responses[2] == {
        "hasNext": True,
        "incremental": [
            {"id": "1", "items": ["slow"]},
            {"id": "2", "items": ["slow"]},
        ],
    }

    assert responses[3] == {
        "hasNext": False,
        "completed": [
            {"id": "1"},
            {
                "id": "2",
                "errors": [
                    {
                        "message": "too slow",
                        "path": ["tasks", 2, "slow"],
                        "extensions": {"status_code": 400},
                    }
                ],
            },
        ],
        "incremental": [
            {"id": "1", "items": ["slow"]},
            {"id": "2", "items": ["slow"]},
        ],
    }
