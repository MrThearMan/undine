from __future__ import annotations

import pytest

from undine import Entrypoint, RootType, create_schema
from undine.typing import PingMessage, PongMessage

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.django_db(transaction=True),  # For sessions
]


# WebSocket


async def test_channels__websocket__connection_init(graphql) -> None:
    async with graphql.websocket() as websocket:
        result = await websocket.connection_init()

    assert result["type"] == "connection_ack"


async def test_channels__websocket__ping(graphql) -> None:
    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        ping = PingMessage(type="ping")
        result = await websocket.send_and_receive(ping)

    assert result["type"] == "pong"


async def test_channels__websocket__pong(graphql) -> None:
    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        ping = PongMessage(type="pong")
        await websocket.send(ping)


async def test_channels__websocket__subscribe(graphql, undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        operation_id = "1"
        data = {"query": "query { test }"}

        result = await websocket.subscribe(data, operation_id=operation_id)
        assert result["type"] == "next"
        assert result["id"] == operation_id
        assert result["payload"] == {"data": {"test": "Hello, World!"}}

        result = await websocket.receive()
        assert result["type"] == "complete"
        assert result["id"] == operation_id


# SSE


async def test_channels__sse__reserve_stream() -> None: ...


async def test_channels__sse__reserve_stream__unauthenticated() -> None: ...


async def test_channels__sse__reserve_stream__already_reserved() -> None: ...


async def test_channels__sse__get_stream() -> None: ...


async def test_channels__sse__get_stream__unauthenticated() -> None: ...


async def test_channels__sse__get_stream__already_open() -> None: ...


async def test_channels__sse__get_stream__stream_not_registered() -> None: ...


async def test_channels__sse__get_stream__wrong_stream_token() -> None: ...


async def test_channels__sse__get_stream__stream_token_missing() -> None: ...


async def test_channels__sse__subscribe() -> None: ...


async def test_channels__sse__subscribe__unauthenticated() -> None: ...


async def test_channels__sse__subscribe__stream_not_registered() -> None: ...


async def test_channels__sse__subscribe__stream_not_opened() -> None: ...


async def test_channels__sse__subscribe__wrong_stream_token() -> None: ...


async def test_channels__sse__subscribe__stream_token_missing() -> None: ...


async def test_channels__sse__subscribe__operation_id_missing() -> None: ...


async def test_channels__sse__subscribe__operation_already_exists() -> None: ...


async def test_channels__sse__cancel_subscription() -> None: ...


async def test_channels__sse__cancel_subscription__unauthenticated() -> None: ...


async def test_channels__sse__cancel_subscription__operation_id_missing() -> None: ...


async def test_channels__sse__cancel_subscription__operation_not_found() -> None: ...


async def test_channels__sse__cancel_subscription__stream_not_registered() -> None: ...


async def test_channels__sse__cancel_subscription__stream_not_opened() -> None: ...


async def test_channels__sse__cancel_subscription__wrong_stream_token() -> None: ...


async def test_channels__sse__cancel_subscription__stream_token_missing() -> None: ...
