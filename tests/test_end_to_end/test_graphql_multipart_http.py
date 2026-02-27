from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest
from graphql import GraphQLError

from undine import Entrypoint, GQLInfo, RootType, create_schema
from undine.exceptions import GraphQLErrorGroup, GraphQLPermissionError

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.django_db(transaction=True),  # For sessions
]


async def test_graphql_multipart_mixed__query(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.ALLOW_QUERIES_WITH_MULTIPART_MIXED = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = "query { test }"

    async for response in graphql_async.multipart_mixed(query):
        assert response.data == {"test": "Hello, World!"}


async def test_graphql_multipart_mixed__query__not_allowed(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.ALLOW_QUERIES_WITH_MULTIPART_MIXED = False

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = "query { test }"

    async for response in graphql_async.multipart_mixed(query):
        assert response.errors == [
            {
                "message": "Cannot use multipart/mixed for queries.",
                "extensions": {
                    "error_code": "CANNOT_USE_MULTIPART_MIXED_FOR_QUERIES",
                    "status_code": 405,
                },
            }
        ]


async def test_graphql_multipart_mixed__mutations(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.ALLOW_MUTATIONS_WITH_MULTIPART_MIXED = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Mutation(RootType):
        @Entrypoint
        async def do_something(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = "mutation { doSomething }"

    async for response in graphql_async.multipart_mixed(query):
        assert response.data == {"doSomething": "Hello, World!"}


async def test_graphql_multipart_mixed__mutations__not_allowed(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.ALLOW_MUTATIONS_WITH_MULTIPART_MIXED = False

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Mutation(RootType):
        @Entrypoint
        async def do_something(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = "mutation { doSomething }"

    async for response in graphql_async.multipart_mixed(query):
        assert response.errors == [
            {
                "message": "Cannot use multipart/mixed for mutations.",
                "extensions": {
                    "error_code": "CANNOT_USE_MULTIPART_MIXED_FOR_MUTATIONS",
                    "status_code": 405,
                },
            }
        ]


async def test_graphql_multipart_mixed__subscription(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

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

    responses = [response.json async for response in graphql_async.multipart_mixed(query)]

    assert responses == [
        {"data": {"countdown": 3}},
        {"data": {"countdown": 2}},
        {"data": {"countdown": 1}},
    ]


async def test_graphql_multipart_mixed__subscription__error(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

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

    responses = [response.json async for response in graphql_async.multipart_mixed(query)]

    assert responses == [
        {"data": {"countdown": 3}},
        {
            "data": None,
            "errors": [
                {
                    "message": "Test error",
                    "path": ["countdown"],
                    "extensions": {"status_code": 400},
                },
            ],
        },
    ]


async def test_graphql_multipart_mixed__subscription__error__as_value(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

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

    responses = [response.json async for response in graphql_async.multipart_mixed(query)]

    assert responses == [
        {"data": {"countdown": 3}},
        {
            "data": None,
            "errors": [
                {
                    "message": "Test error",
                    "path": ["countdown"],
                    "extensions": {"status_code": 400},
                },
            ],
        },
        {"data": {"countdown": 1}},
    ]


async def test_graphql_multipart_mixed__subscription__error_group(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

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

    responses = [response.json async for response in graphql_async.multipart_mixed(query)]

    assert responses == [
        {"data": {"countdown": 3}},
        {
            "data": None,
            "errors": [
                {
                    "message": "Real error",
                    "path": ["countdown"],
                    "extensions": {"status_code": 400},
                },
                {
                    "message": "Test error",
                    "path": ["countdown"],
                    "extensions": {"status_code": 400},
                },
            ],
        },
    ]


async def test_graphql_multipart_mixed__subscription__error_group__as_value(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

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

    responses = [response.json async for response in graphql_async.multipart_mixed(query)]

    assert responses == [
        {"data": {"countdown": 3}},
        {
            "data": None,
            "errors": [
                {
                    "message": "Real error",
                    "path": ["countdown"],
                    "extensions": {"status_code": 400},
                },
                {
                    "message": "Test error",
                    "path": ["countdown"],
                    "extensions": {"status_code": 400},
                },
            ],
        },
        {"data": {"countdown": 1}},
    ]


async def test_graphql_multipart_mixed__subscription__error__permissions(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

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

    responses = [response.json async for response in graphql_async.multipart_mixed(query)]

    assert responses == [
        {
            "data": None,
            "errors": [
                {
                    "message": "Permission denied.",
                    "path": ["countdown"],
                    "extensions": {"error_code": "PERMISSION_DENIED", "status_code": 403},
                }
            ],
        }
    ]
