from __future__ import annotations

from typing import AsyncIterator

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import Entrypoint, Field, QueryType, RootType, create_schema
from undine.optimizer import OptimizationData
from undine.typing import GQLInfo


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_end_to_end__async_iterator_field(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        async def echo(self: Task) -> AsyncIterator[str]:
            for _ in range(self.points):
                yield "hello"

        @echo.optimize
        def echo_optimized(self: Field, data: OptimizationData, info: GQLInfo) -> None:
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
            echo
          }
        }
    """

    response = await graphql_async(query)

    assert response.json == {
        "data": {
            "tasks": [
                {"name": "foo", "echo": ["hello"]},
                {"name": "bar", "echo": ["hello", "hello"]},
                {"name": "baz", "echo": ["hello", "hello", "hello"]},
            ]
        }
    }
