from __future__ import annotations

import asyncio
import time

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import Entrypoint, Field, QueryType, RootType, create_schema


@pytest.mark.django_db(transaction=True)
async def test_execution_timeout(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.EXECUTION_TIMEOUT_SECONDS = 0.05

    class Query(RootType):
        @Entrypoint
        async def slow(self) -> str:
            await asyncio.sleep(5)
            return "slow"

    undine_settings.SCHEMA = create_schema(query=Query)

    response = await graphql_async("query { slow }")

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "GraphQL operation execution timed out",
                "extensions": {"status_code": 408, "error_code": "EXECUTION_TIMEOUT"},
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_execution_timeout__finishes_in_time(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.EXECUTION_TIMEOUT_SECONDS = 5

    class Query(RootType):
        @Entrypoint
        async def fast(self) -> str:
            return "fast"

    undine_settings.SCHEMA = create_schema(query=Query)

    response = await graphql_async("query { fast }")

    assert response.json == {"data": {"fast": "fast"}}


@pytest.mark.django_db(transaction=True)
async def test_execution_timeout__executor_build_error(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.EXECUTION_TIMEOUT_SECONDS = 5

    class Query(RootType):
        @Entrypoint
        async def example(self, value: int) -> int:
            return value

    undine_settings.SCHEMA = create_schema(query=Query)

    response = await graphql_async("query ($value: Int!) { example(value: $value) }", variables={"value": "foo"})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Variable '$value' has invalid value: Int cannot represent non-integer value: 'foo'",
                "extensions": {"status_code": 400},
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_execution_timeout__deferred_fields(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.EXECUTION_TIMEOUT_SECONDS = 0.05

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        async def slow(self: Task) -> str:
            await asyncio.sleep(5)
            return "slow"

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="foo")
    await sync_to_async(TaskFactory.create)(name="bar")

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

    error = {
        "message": "GraphQL operation execution timed out",
        "extensions": {"status_code": 408, "error_code": "EXECUTION_TIMEOUT"},
    }

    assert responses == [
        {
            "hasNext": True,
            "data": {
                "tasks": [
                    {"name": "foo"},
                    {"name": "bar"},
                ],
            },
            "pending": [
                {"id": "0", "path": ["tasks", 0]},
                {"id": "1", "path": ["tasks", 1]},
            ],
        },
        {
            "hasNext": False,
            "completed": [
                {"id": "0", "errors": [error]},
                {"id": "1", "errors": [error]},
            ],
        },
    ]


@pytest.mark.django_db(transaction=True)
async def test_execution_timeout__nested_deferred_fields(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.EXECUTION_TIMEOUT_SECONDS = 0.05

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        async def fast(self: Task) -> str:
            return "fast"

        @Field
        async def slow(self: Task) -> str:
            await asyncio.sleep(5)
            return "slow"

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="foo")

    query = """
        query {
          tasks {
            name
            ... @defer {
              fast
              ... @defer {
                slow
              }
            }
          }
        }
    """

    responses = [response.json async for response in graphql_async.incremental_delivery(query)]

    assert responses == [
        {
            "hasNext": True,
            "data": {"tasks": [{"name": "foo"}]},
            "pending": [{"id": "0", "path": ["tasks", 0]}],
        },
        {
            "hasNext": True,
            "pending": [{"id": "1", "path": ["tasks", 0]}],
            "incremental": [{"id": "0", "data": {"fast": "fast"}}],
            "completed": [{"id": "0"}],
        },
        {
            # Only the nested result was still pending when the time ran out.
            "hasNext": False,
            "completed": [
                {
                    "id": "1",
                    "errors": [
                        {
                            "message": "GraphQL operation execution timed out",
                            "extensions": {"status_code": 408, "error_code": "EXECUTION_TIMEOUT"},
                        },
                    ],
                },
            ],
        },
    ]


@pytest.mark.django_db
def test_execution_timeout__sync(graphql, undine_settings) -> None:
    undine_settings.EXECUTION_TIMEOUT_SECONDS = 0.01

    class Query(RootType):
        @Entrypoint
        def slow(self) -> str:
            time.sleep(0.05)
            return "slow"

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query { slow }")

    # Sync execution cannot be interrupted, so the timeout doesn't apply.
    assert response.json == {"data": {"slow": "slow"}}
