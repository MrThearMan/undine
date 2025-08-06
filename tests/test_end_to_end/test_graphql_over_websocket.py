from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest
from graphql import FormattedExecutionResult, GraphQLError, GraphQLFormattedError

from undine import Entrypoint, GQLInfo, RootType, create_schema
from undine.exceptions import GraphQLErrorGroup, GraphQLPermissionError

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.django_db(transaction=True),  # For sessions
]


async def test_graphql_over_websocket(graphql, undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = "query { test }"

    async for response in graphql.over_websocket(query):
        assert response.data == {"test": "Hello, World!"}


async def test_graphql_over_websocket__subscription(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncGenerator[int, None]:
            for i in range(3, 0, -1):
                await asyncio.sleep(0)
                yield i

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    query = "subscription { countdown }"

    responses = [response.json async for response in graphql.over_websocket(query)]
    expected = [
        FormattedExecutionResult(data={"countdown": 3}),
        FormattedExecutionResult(data={"countdown": 2}),
        FormattedExecutionResult(data={"countdown": 1}),
    ]

    assert responses == expected


async def test_graphql_over_websocket__subscription__error(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncGenerator[int, None]:
            for i in range(3, 0, -1):
                if i == 2:
                    msg = "Test error"
                    raise GraphQLError(msg)
                yield i

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    query = "subscription { countdown }"

    responses = [response.json async for response in graphql.over_websocket(query)]
    expected = [
        FormattedExecutionResult(data={"countdown": 3}),
        FormattedExecutionResult(
            data=None,
            errors=[
                GraphQLFormattedError(message="Test error", path=["countdown"]),
            ],
        ),
    ]

    assert responses == expected


async def test_graphql_over_websocket__subscription__error__as_value(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncGenerator[int | GraphQLError, None]:
            for i in range(3, 0, -1):
                if i == 2:
                    msg = "Test error"
                    yield GraphQLError(msg)
                else:
                    yield i

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    query = "subscription { countdown }"

    responses = [response.json async for response in graphql.over_websocket(query)]
    expected = [
        FormattedExecutionResult(data={"countdown": 3}),
        FormattedExecutionResult(
            data=None,
            errors=[
                GraphQLFormattedError(
                    message="Test error",
                    path=["countdown"],
                    extensions={"status_code": 400},
                ),
            ],
        ),
        FormattedExecutionResult(data={"countdown": 1}),
    ]

    assert responses == expected


async def test_graphql_over_websocket__subscription__error_group(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncGenerator[int, None]:
            for i in range(3, 0, -1):
                if i == 2:
                    msg_1 = "Test error"
                    msg_2 = "Real error"
                    error_1 = GraphQLError(msg_1)
                    error_2 = GraphQLError(msg_2)
                    raise GraphQLErrorGroup([error_1, error_2])
                yield i

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    query = "subscription { countdown }"

    responses = [response.json async for response in graphql.over_websocket(query)]
    expected = [
        FormattedExecutionResult(data={"countdown": 3}),
        FormattedExecutionResult(
            data=None,
            errors=[
                GraphQLFormattedError(message="Test error", path=["countdown"]),
                GraphQLFormattedError(message="Real error", path=["countdown"]),
            ],
        ),
    ]

    assert responses == expected


async def test_graphql_over_websocket__subscription__error_group__as_value(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncGenerator[int | GraphQLErrorGroup, None]:
            for i in range(3, 0, -1):
                if i == 2:
                    msg_1 = "Test error"
                    msg_2 = "Real error"
                    error_1 = GraphQLError(msg_1)
                    error_2 = GraphQLError(msg_2)
                    yield GraphQLErrorGroup([error_1, error_2])
                else:
                    yield i

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    query = "subscription { countdown }"

    responses = [response.json async for response in graphql.over_websocket(query)]
    expected = [
        FormattedExecutionResult(data={"countdown": 3}),
        FormattedExecutionResult(
            data=None,
            errors=[
                GraphQLFormattedError(
                    message="Real error",
                    path=["countdown"],
                    extensions={"status_code": 400},
                ),
                GraphQLFormattedError(
                    message="Test error",
                    path=["countdown"],
                    extensions={"status_code": 400},
                ),
            ],
        ),
        FormattedExecutionResult(data={"countdown": 1}),
    ]

    assert responses == expected


async def test_graphql_over_websocket__subscription__error__permissions(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncGenerator[int, None]:
            for i in range(3, 0, -1):
                yield i

        @countdown.permissions
        def countdown_permissions(self, info: GQLInfo, value: int) -> None:
            raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    query = "subscription { countdown }"

    responses = [response.json async for response in graphql.over_websocket(query)]
    expected = [
        FormattedExecutionResult(
            data=None,
            errors=[
                GraphQLFormattedError(
                    message="Permission denied.",
                    path=["countdown"],
                    extensions={
                        "status_code": 403,
                        "error_code": "PERMISSION_DENIED",
                    },
                ),
            ],
        ),
    ]

    assert responses == expected


async def test_graphql_over_websocket__subscription__unsubscribe(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    counted: list[int] = []

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncGenerator[int, None]:
            nonlocal counted
            for i in range(100, 0, -1):
                await asyncio.sleep(0.001)
                counted.append(i)
                yield i

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    operation_id = "1"
    body = {"query": "subscription { countdown }"}

    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        # Subscribe
        result = await websocket.subscribe(body, operation_id=operation_id)
        assert result["type"] == "next"
        assert result["payload"] == FormattedExecutionResult(data={"countdown": 100})
        assert operation_id in websocket.consumer.handler.operations

        # Unsubscribe and wait it to take effect
        await websocket.unsubscribe(operation_id=operation_id)
        with pytest.raises(asyncio.CancelledError):
            await websocket.consumer.handler.operations[operation_id].task
        assert operation_id not in websocket.consumer.handler.operations

    # It's not guaranteed at which point the unsubscribe will complete (usually withing 1-2 messages
    # from the subscription), but it should be completed before the subscription is completed.
    assert len(counted) < 100
