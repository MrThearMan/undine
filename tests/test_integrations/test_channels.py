from __future__ import annotations

import asyncio
import json
import uuid
from http import HTTPStatus

import pytest
from django.conf import settings as django_settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import caches

from tests.test_integrations.helpers import (
    _create_session,
    _create_user,
    _open_stream,
    _reserve_stream,
    get_graphql_sse_operation_router,
    get_graphql_sse_router,
    make_http_scope,
    make_sse_communicator,
    sse_get_response,
    sse_send_request,
)
from undine import Entrypoint, RootType, create_schema
from undine.http.utils import HttpMethodNotAllowedResponse, HttpUnsupportedContentTypeResponse
from undine.typing import PingMessage, PongMessage, RequestMethod, SSEState
from undine.utils.graphql.server_sent_events import (
    get_sse_operation_claim_key,
    get_sse_operation_key,
    get_sse_stream_claim_key,
    get_sse_stream_state_key,
    get_sse_stream_token_key,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.django_db(transaction=True),
]


@pytest.fixture(autouse=True)
def _clear_sse_cache():
    """Handle clearing the session cache between runs so that cache data is not shared between tests."""
    yield
    cache = caches[django_settings.SESSION_CACHE_ALIAS]
    cache.clear()


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


# SSE - Authentication


async def test_channels__sse__consumer_stopped_when_unauthenticated() -> None:
    session = await _create_session()

    communicator = make_sse_communicator(
        method="PUT",
        headers=[(b"accept", b"text/plain")],
        user=AnonymousUser(),
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.UNAUTHORIZED
    assert response["json"]["errors"][0]["message"] == (
        "GraphQL over SSE requires authentication in single connection mode"
    )

    # handle() was never called — session remains untouched
    assert await session.aget(get_sse_stream_token_key()) is None
    assert await session.aget(get_sse_stream_state_key()) is None


# SSE - Reserve Stream


async def test_channels__sse__reserve_stream(undine_settings) -> None:
    user = await _create_user()
    session = await _create_session(user)

    communicator = make_sse_communicator(
        method="PUT",
        headers=[(b"accept", b"text/plain")],
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.CREATED
    assert uuid.UUID(response["body"])

    # Verify session was updated
    stream_token = await session.aget(get_sse_stream_token_key())
    stream_state = await session.aget(get_sse_stream_state_key())
    assert stream_state == SSEState.REGISTERED
    assert stream_token == response["body"]


async def test_channels__sse__reserve_stream__unauthenticated() -> None:
    session = await _create_session()

    communicator = make_sse_communicator(
        method="PUT",
        headers=[(b"accept", b"text/plain")],
        user=AnonymousUser(),
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.UNAUTHORIZED
    assert response["json"]["errors"][0]["message"] == (
        "GraphQL over SSE requires authentication in single connection mode"
    )


async def test_channels__sse__reserve_stream__already_reserved() -> None:
    user = await _create_user()
    session = await _create_session(user)

    # Reserve first
    old_token = await _reserve_stream(user, session)

    # Re-reserving replaces the stale REGISTERED state with a new token
    communicator = make_sse_communicator(
        method="PUT",
        headers=[(b"accept", b"text/plain")],
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.CREATED
    new_token = response["body"]
    assert uuid.UUID(new_token)
    assert new_token != old_token

    stream_token = await session.aget(get_sse_stream_token_key())
    stream_state = await session.aget(get_sse_stream_state_key())
    assert stream_state == SSEState.REGISTERED
    assert stream_token == new_token


async def test_channels__sse__reserve_stream__stale_opened_state(undine_settings) -> None:
    user = await _create_user()
    session = await _create_session(user)

    # Simulate stale OPENED state left in the session (e.g. from a race condition on disconnect)
    await session.aset(key=get_sse_stream_token_key(), value="stale-token")
    await session.aset(key=get_sse_stream_state_key(), value=SSEState.OPENED)
    await session.asave()

    # Reserve should succeed, cleaning up the stale state
    communicator = make_sse_communicator(
        method="PUT",
        headers=[(b"accept", b"text/plain")],
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.CREATED
    assert uuid.UUID(response["body"])

    # Verify stale operation key was cleaned up
    stream_operation_key = get_sse_operation_key(operation_id="op-1")
    assert await session.aget(stream_operation_key) is None

    # Verify new stream state
    stream_token = await session.aget(get_sse_stream_token_key())
    stream_state = await session.aget(get_sse_stream_state_key())
    assert stream_state == SSEState.REGISTERED
    assert stream_token == response["body"]


async def test_channels__sse__reserve_stream__stale_registered_operation() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)

    # Simulate an operation optimistically saved while stream was REGISTERED
    # (e.g. operation submitted before stream opened, then timed out after
    # a new stream was reserved, so the rollback skipped this key).
    operation_key = get_sse_operation_key(operation_id="op-1")
    await session.aset(key=operation_key, value="ok")
    await session.asave()

    # Re-reserving from REGISTERED state should clean up stale operations
    new_token = await _reserve_stream(user, session)
    assert new_token != token

    await session.aload()
    assert await session.aget(operation_key) is None


# SSE - Get Stream


async def test_channels__sse__get_stream(undine_settings) -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)

    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=f"token={token}".encode(),
        user=user,
        session=session,
    )
    await sse_send_request(communicator)

    start = await communicator.receive_output(timeout=3)
    assert start["type"] == "http.response.start"
    assert start["status"] == HTTPStatus.OK

    headers = {k.decode(): v.decode() for k, v in start.get("headers", [])}
    assert "text/event-stream" in headers.get("Content-Type", "")

    # First body event (SSE comment keep-alive, keeps connection open)
    body_event = await communicator.receive_output(timeout=3)
    assert body_event["type"] == "http.response.body"
    assert body_event["body"] == b":\n\n"
    assert body_event.get("more_body") is True

    # Verify session was updated
    stream_token = await session.aget(get_sse_stream_token_key())
    stream_state = await session.aget(get_sse_stream_state_key())
    assert stream_state == SSEState.OPENED
    assert stream_token == token


async def test_channels__sse__get_stream__unauthenticated() -> None:
    session = await _create_session()

    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=b"token=some-token",
        user=AnonymousUser(),
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.UNAUTHORIZED
    assert response["json"]["errors"][0]["message"] == (
        "GraphQL over SSE requires authentication in single connection mode"
    )


async def test_channels__sse__get_stream__already_open() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)

    # Open stream first
    await _open_stream(user, session, token)

    # Try to open again
    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=f"token={token}".encode(),
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.CONFLICT
    assert response["json"]["errors"][0]["message"] == "Stream already open"


async def test_channels__sse__get_stream__concurrent_open_blocked_by_cache_claim() -> None:
    """When another worker has already claimed the stream via cache, a second open attempt is rejected."""
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)

    # Simulate another worker having already claimed this stream in the cache.
    cache = caches[django_settings.SESSION_CACHE_ALIAS]
    cache_key = get_sse_stream_claim_key(token)
    assert await cache.aadd(cache_key, "1", timeout=1800)

    # Session still says REGISTERED, but cache claim blocks the open.
    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=f"token={token}".encode(),
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.CONFLICT
    assert response["json"]["errors"][0]["message"] == "Stream already open"


async def test_channels__sse__get_stream__cache_claim_released_after_session_save() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)

    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=f"token={token}".encode(),
        user=user,
        session=session,
    )
    await sse_send_request(communicator)

    start = await communicator.receive_output(timeout=3)
    assert start["status"] == HTTPStatus.OK

    # Cache claim should already be released once the session contains the state.
    cache = caches[django_settings.SESSION_CACHE_ALIAS]
    cache_key = get_sse_stream_claim_key(token)
    assert await cache.aget(cache_key) is None


async def test_channels__sse__get_stream__stream_not_registered() -> None:
    user = await _create_user()
    session = await _create_session(user)

    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=b"token=nonexistent-token",
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.NOT_FOUND
    assert response["json"]["errors"][0]["message"] == "Stream not found"


async def test_channels__sse__get_stream__wrong_stream_token() -> None:
    user = await _create_user()
    session = await _create_session(user)

    # Reserve stream, but try to open with wrong token
    await _reserve_stream(user, session)

    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=b"token=wrong-token",
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.NOT_FOUND
    assert response["json"]["errors"][0]["message"] == "Stream not found"


async def test_channels__sse__get_stream__stream_token_missing() -> None:
    user = await _create_user()
    session = await _create_session(user)
    await _reserve_stream(user, session)

    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.BAD_REQUEST
    assert response["json"]["errors"][0]["message"] == "Stream token missing"


# SSE - Keep-alive pings


async def test_channels__sse__keep_alive_ping(undine_settings) -> None:
    undine_settings.SSE_KEEP_ALIVE_INTERVAL = 0.01  # type: ignore[assignment]

    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)

    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=f"token={token}".encode(),
        user=user,
        session=session,
    )
    await sse_send_request(communicator)

    # Consume response start + initial SSE comment
    await communicator.receive_output(timeout=3)
    await communicator.receive_output(timeout=3)

    # Wait for the first periodic keep-alive ping
    ping = await communicator.receive_output(timeout=3)
    assert ping["type"] == "http.response.body"
    assert ping["body"] == b":\n\n"
    assert ping.get("more_body") is True


async def test_channels__sse__keep_alive_ping__disabled(undine_settings) -> None:
    undine_settings.SSE_KEEP_ALIVE_INTERVAL = 0

    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)

    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=f"token={token}".encode(),
        user=user,
        session=session,
    )
    await sse_send_request(communicator)

    # Consume response start + initial SSE comment
    await communicator.receive_output(timeout=3)
    await communicator.receive_output(timeout=3)

    # No periodic ping should arrive
    with pytest.raises(asyncio.TimeoutError):
        await communicator.receive_output(timeout=0.01)


# SSE - Subscribe


async def test_channels__sse__subscribe(undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_SSE = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    body = json.dumps({
        "query": "query { test }",
        "extensions": {"operationId": "op-1"},
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", token.encode()),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.ACCEPTED


async def test_channels__sse__subscribe__unauthenticated() -> None:
    session = await _create_session()

    body = json.dumps({
        "query": "subscription { test }",
        "extensions": {"operationId": "op-1"},
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", b"some-token"),
        ],
        user=AnonymousUser(),
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.UNAUTHORIZED
    assert response["json"]["errors"][0]["message"] == (
        "GraphQL over SSE requires authentication in single connection mode"
    )


async def test_channels__sse__subscribe__stream_not_registered() -> None:
    user = await _create_user()
    session = await _create_session(user)

    body = json.dumps({
        "query": "subscription { test }",
        "extensions": {"operationId": "op-1"},
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", b"nonexistent-token"),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.NOT_FOUND
    assert response["json"]["errors"][0]["message"] == "Stream not found"


async def test_channels__sse__subscribe__stream_did_not_open_in_time(undine_settings) -> None:
    undine_settings.SSE_OPERATION_STREAM_OPEN_TIMEOUT = 0.1  # type: ignore[assignment]

    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    operation_id = "op-1"

    body = json.dumps({
        "query": "subscription { test }",
        "extensions": {"operationId": operation_id},
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", token.encode()),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    # The operation waits for the stream to open before responding.
    # If the stream never opens, the client gets a 409 instead of 202.
    assert response["status"] == HTTPStatus.CONFLICT
    assert response["json"]["errors"][0]["message"] == "Operation timed out before stream was opened"

    # Let the operation cleanup (finally block) finish before checking session.
    await asyncio.sleep(0.05)

    # Operation should not be saved in the session since it was rejected.
    operation_key = get_sse_operation_key(operation_id=operation_id)
    await session.aload()
    assert await session.aget(operation_key) is None


async def test_channels__sse__subscribe__before_stream_opened(undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_SSE = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)

    body = json.dumps({
        "query": "query { test }",
        "extensions": {"operationId": "op-1"},
    }).encode()

    op_communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", token.encode()),
        ],
        user=user,
        session=session,
    )
    # The POST waits for the stream to open before responding with 202,
    # so send it first, then open the stream concurrently.
    await sse_send_request(op_communicator, body=body)

    await asyncio.sleep(0)

    stream_communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=f"token={token}".encode(),
        user=user,
        session=session,
    )
    await sse_send_request(stream_communicator)

    start = await stream_communicator.receive_output(timeout=3)
    assert start["type"] == "http.response.start"
    assert start["status"] == HTTPStatus.OK

    # The operation is accepted only after the stream opens.
    response = await sse_get_response(op_communicator)
    assert response["status"] == HTTPStatus.ACCEPTED

    body_event = await stream_communicator.receive_output(timeout=3)
    assert body_event["type"] == "http.response.body"
    assert body_event["body"] == b":\n\n"
    assert body_event.get("more_body") is True

    event = await stream_communicator.receive_output(timeout=5)
    assert event["type"] == "http.response.body"
    assert b"event: next" in event["body"]
    assert b'"Hello, World!"' in event["body"]


async def test_channels__sse__subscribe__wrong_stream_token() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    body = json.dumps({
        "query": "subscription { test }",
        "extensions": {"operationId": "op-1"},
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", b"wrong-token"),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.NOT_FOUND
    assert response["json"]["errors"][0]["message"] == "Stream not found"


async def test_channels__sse__subscribe__stream_token_missing() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    body = json.dumps({
        "query": "subscription { test }",
        "extensions": {"operationId": "op-1"},
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.BAD_REQUEST
    assert response["json"]["errors"][0]["message"] == "Stream token missing"


async def test_channels__sse__subscribe__operation_id_missing() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    body = json.dumps({
        "query": "subscription { test }",
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", token.encode()),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.BAD_REQUEST
    assert response["json"]["errors"][0]["message"] == "Operation ID is missing"


async def test_channels__sse__subscribe__operation_already_exists(undine_settings) -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    operation_id = "op-1"

    # Mark operation as already existing in session
    operation_key = get_sse_operation_key(operation_id=operation_id)
    await session.aset(key=operation_key, value="ok")
    await session.asave()

    body = json.dumps({
        "query": "subscription { test }",
        "extensions": {"operationId": operation_id},
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", token.encode()),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.CONFLICT
    assert response["json"]["errors"][0]["message"] == "Operation with ID already exists"


async def test_channels__sse__subscribe__concurrent_operation_blocked_by_cache_claim() -> None:
    """When another worker has already claimed an operation ID via cache, a duplicate is rejected."""
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    operation_id = "op-dup"

    # Simulate another worker having already claimed this operation in the cache.
    cache = caches[django_settings.SESSION_CACHE_ALIAS]
    cache_key = get_sse_operation_claim_key(token, operation_id)
    assert await cache.aadd(cache_key, "1", timeout=1800)

    body = json.dumps({
        "query": "subscription { test }",
        "extensions": {"operationId": operation_id},
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", token.encode()),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.CONFLICT
    assert response["json"]["errors"][0]["message"] == "Operation with ID already exists"


async def test_channels__sse__subscribe__cache_claim_released_after_session_save(undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_SSE = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    operation_id = "op-release"

    body = json.dumps({
        "query": "query { test }",
        "extensions": {"operationId": operation_id},
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", token.encode()),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)
    assert response["status"] == HTTPStatus.ACCEPTED

    # Cache claim should already be released once the session contains the operation.
    cache = caches[django_settings.SESSION_CACHE_ALIAS]
    cache_key = get_sse_operation_claim_key(token, operation_id)
    assert await cache.aget(cache_key) is None


# SSE - Cancel Subscription


async def test_channels__sse__cancel_subscription() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    communicator = make_sse_communicator(
        method="DELETE",
        headers=[(b"x-graphql-event-stream-token", token.encode())],
        query_string=b"operationId=op-1",
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.OK


async def test_channels__sse__cancel_subscription__unauthenticated() -> None:
    session = await _create_session()

    communicator = make_sse_communicator(
        method="DELETE",
        headers=[(b"x-graphql-event-stream-token", b"some-token")],
        query_string=b"operationId=op-1",
        user=AnonymousUser(),
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.UNAUTHORIZED
    assert response["json"]["errors"][0]["message"] == (
        "GraphQL over SSE requires authentication in single connection mode"
    )


async def test_channels__sse__cancel_subscription__operation_id_missing() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    communicator = make_sse_communicator(
        method="DELETE",
        headers=[(b"x-graphql-event-stream-token", token.encode())],
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.BAD_REQUEST
    assert response["json"]["errors"][0]["message"] == "Operation ID is missing"


async def test_channels__sse__cancel_subscription__operation_not_found() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    communicator = make_sse_communicator(
        method="DELETE",
        headers=[(b"x-graphql-event-stream-token", token.encode())],
        query_string=b"operationId=nonexistent",
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    # cancel_operation sends to the group but there's no consumer listening,
    # so it just succeeds silently
    assert response["status"] == HTTPStatus.OK


async def test_channels__sse__cancel_subscription__stream_not_registered() -> None:
    user = await _create_user()
    session = await _create_session(user)

    communicator = make_sse_communicator(
        method="DELETE",
        headers=[(b"x-graphql-event-stream-token", b"nonexistent-token")],
        query_string=b"operationId=op-1",
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.NOT_FOUND
    assert response["json"]["errors"][0]["message"] == "Stream not found"


async def test_channels__sse__cancel_subscription__stream_not_opened() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)

    communicator = make_sse_communicator(
        method="DELETE",
        headers=[(b"x-graphql-event-stream-token", token.encode())],
        query_string=b"operationId=op-1",
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    # The spec allows cancellation before the stream is actually opened.
    # Targets the operation's own channel group, independent of stream state.
    assert response["status"] == HTTPStatus.OK


async def test_channels__sse__cancel_subscription__before_stream_opened(undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_SSE = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    operation_id = "op-1"

    body = json.dumps({
        "query": "query { test }",
        "extensions": {"operationId": operation_id},
    }).encode()

    # Submit operation (queued, waiting for stream to open)
    op_communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", token.encode()),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(op_communicator, body=body)

    # Let the operation consumer complete handle() — it needs multiple
    # yields for session save and channel group joins.
    await asyncio.sleep(0.05)

    # Cancel the queued operation
    cancel_communicator = make_sse_communicator(
        method="DELETE",
        headers=[(b"x-graphql-event-stream-token", token.encode())],
        query_string=f"operationId={operation_id}".encode(),
        user=user,
        session=session,
    )
    await sse_send_request(cancel_communicator)
    cancel_response = await sse_get_response(cancel_communicator)
    assert cancel_response["status"] == HTTPStatus.OK

    # Let the cancel signal propagate through the channel layer and
    # the operation consumer's dispatch loop (needs multiple yields).
    await asyncio.sleep(0.05)

    # Open the stream
    stream_communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=f"token={token}".encode(),
        user=user,
        session=session,
    )
    await sse_send_request(stream_communicator)

    start = await stream_communicator.receive_output(timeout=3)
    assert start["type"] == "http.response.start"
    assert start["status"] == HTTPStatus.OK

    body_event = await stream_communicator.receive_output(timeout=3)
    assert body_event["type"] == "http.response.body"
    assert body_event["body"] == b":\n\n"
    assert body_event.get("more_body") is True

    # No operation events should arrive on the stream
    with pytest.raises(asyncio.TimeoutError):
        await stream_communicator.receive_output(timeout=0.5)

    # Operation should be cleaned from the session
    await session.aload()
    assert await session.aget(get_sse_operation_key(operation_id=operation_id)) is None


async def test_channels__sse__cancel_subscription__wrong_stream_token() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    communicator = make_sse_communicator(
        method="DELETE",
        headers=[(b"x-graphql-event-stream-token", b"wrong-token")],
        query_string=b"operationId=op-1",
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.NOT_FOUND
    assert response["json"]["errors"][0]["message"] == "Stream not found"


async def test_channels__sse__cancel_subscription__stream_token_missing() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    communicator = make_sse_communicator(
        method="DELETE",
        query_string=b"operationId=op-1",
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.BAD_REQUEST
    assert response["json"]["errors"][0]["message"] == "Stream token missing"


# SSE Router


async def test_channels__sse_router__non_graphql_path_routes_to_asgi() -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(path="/other/")

    await router(scope, None, None)

    router.django_application.assert_awaited_once()
    router.sse_application.assert_not_awaited()


@pytest.mark.parametrize("http_version", ["1.1", "2.0"])
async def test_channels__sse_router__put_routes_to_sse(http_version) -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(
        method="PUT",
        http_version=http_version,  # type: ignore[arg-type]
    )

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.django_application.assert_not_awaited()


@pytest.mark.parametrize("http_version", ["1.1", "2.0"])
async def test_channels__sse_router__delete_routes_to_sse(http_version) -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(
        method="DELETE",
        http_version=http_version,  # type: ignore[arg-type]
    )

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.django_application.assert_not_awaited()


@pytest.mark.parametrize("http_version", ["1.1", "2.0"])
async def test_channels__sse_router__get_with_token_query_param_routes_to_sse(http_version) -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(
        method="GET",
        query_string=b"token=some-token",
        http_version=http_version,  # type: ignore[arg-type]
    )

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.django_application.assert_not_awaited()


@pytest.mark.parametrize("http_version", ["1.1", "2.0"])
async def test_channels__sse_router__get_with_token_header_routes_to_sse(http_version) -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(
        method="GET",
        headers=[(b"x-graphql-event-stream-token", b"some-token")],
        http_version=http_version,  # type: ignore[arg-type]
    )

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.django_application.assert_not_awaited()


@pytest.mark.parametrize("http_version", ["1.1", "2.0"])
async def test_channels__sse_router__post_with_token_query_param_routes_to_sse(http_version) -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(
        method="POST",
        query_string=b"token=some-token",
        http_version=http_version,  # type: ignore[arg-type]
    )

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.django_application.assert_not_awaited()


@pytest.mark.parametrize("http_version", ["1.1", "2.0"])
async def test_channels__sse_router__post_with_token_header_routes_to_sse(http_version) -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(
        method="POST",
        headers=[(b"x-graphql-event-stream-token", b"some-token")],
        http_version=http_version,  # type: ignore[arg-type]
    )

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.django_application.assert_not_awaited()


@pytest.mark.parametrize("http_version", ["1.1", "2.0"])
async def test_channels__sse_router__get_without_token_routes_to_asgi(http_version) -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(
        method="GET",
        http_version=http_version,  # type: ignore[arg-type]
    )

    await router(scope, None, None)

    router.django_application.assert_awaited_once()
    router.sse_application.assert_not_awaited()


@pytest.mark.parametrize("http_version", ["1.1", "2.0"])
async def test_channels__sse_router__post_without_token_routes_to_asgi(http_version) -> None:
    router = get_graphql_sse_router()
    scope = make_http_scope(
        method="POST",
        http_version=http_version,  # type: ignore[arg-type]
    )

    await router(scope, None, None)

    router.django_application.assert_awaited_once()
    router.sse_application.assert_not_awaited()


# SSE Operation Router


async def test_channels__sse_operation_router__non_accepted_method(undine_settings) -> None:
    router = get_graphql_sse_operation_router()
    scope = make_http_scope(method="HEAD")

    await router(scope, None, None)

    router.send_http_response.assert_awaited_once()
    router.stream_reservation_consumer.assert_not_awaited()
    router.event_stream_consumer.assert_not_awaited()
    router.operation_consumer.assert_not_awaited()
    router.operation_cancellation_consumer.assert_not_awaited()

    response = router.send_http_response.await_args.kwargs["response"]
    assert isinstance(response, HttpMethodNotAllowedResponse)


async def test_channels__sse_operation_router__stream_reservation(undine_settings) -> None:
    router = get_graphql_sse_operation_router()
    scope = make_http_scope(method="PUT", headers=[(b"accept", b"text/plain")])

    await router(scope, None, None)

    router.send_http_response.assert_not_awaited()
    router.stream_reservation_consumer.assert_awaited_once()
    router.event_stream_consumer.assert_not_awaited()
    router.operation_consumer.assert_not_awaited()
    router.operation_cancellation_consumer.assert_not_awaited()


async def test_channels__sse_operation_router__stream_reservation__doesnt_accept_test_plain(undine_settings) -> None:
    router = get_graphql_sse_operation_router()
    scope = make_http_scope(method="PUT", headers=[(b"accept", b"application/json")])

    await router(scope, None, None)

    router.send_http_response.assert_awaited_once()
    router.stream_reservation_consumer.assert_not_awaited()
    router.event_stream_consumer.assert_not_awaited()
    router.operation_consumer.assert_not_awaited()
    router.operation_cancellation_consumer.assert_not_awaited()

    response = router.send_http_response.await_args.kwargs["response"]
    assert isinstance(response, HttpUnsupportedContentTypeResponse)


@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_channels__sse_operation_router__event_stream(method: RequestMethod) -> None:
    router = get_graphql_sse_operation_router()
    scope = make_http_scope(method=method, headers=[(b"accept", b"text/event-stream")])

    await router(scope, None, None)

    router.send_http_response.assert_not_awaited()
    router.stream_reservation_consumer.assert_not_awaited()
    router.event_stream_consumer.assert_awaited_once()
    router.operation_consumer.assert_not_awaited()
    router.operation_cancellation_consumer.assert_not_awaited()


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize("accept", [b"application/json", b"application/*", b"*/*"])
async def test_channels__sse_operation_router__operation(method: RequestMethod, accept: bytes) -> None:
    router = get_graphql_sse_operation_router()
    scope = make_http_scope(method=method, headers=[(b"accept", accept)])

    await router(scope, None, None)

    router.send_http_response.assert_not_awaited()
    router.stream_reservation_consumer.assert_not_awaited()
    router.event_stream_consumer.assert_not_awaited()
    router.operation_consumer.assert_awaited_once()
    router.operation_cancellation_consumer.assert_not_awaited()


@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_channels__sse_operation_router__operation__cannot_accept_json(method: RequestMethod) -> None:
    router = get_graphql_sse_operation_router()
    scope = make_http_scope(method=method, headers=[(b"accept", b"text/html")])

    await router(scope, None, None)

    router.send_http_response.assert_awaited_once()
    router.stream_reservation_consumer.assert_not_awaited()
    router.event_stream_consumer.assert_not_awaited()
    router.operation_consumer.assert_not_awaited()
    router.operation_cancellation_consumer.assert_not_awaited()

    response = router.send_http_response.await_args.kwargs["response"]
    assert isinstance(response, HttpUnsupportedContentTypeResponse)


async def test_channels__sse_operation_router__cancellation(undine_settings) -> None:
    router = get_graphql_sse_operation_router()
    scope = make_http_scope(method="DELETE")

    await router(scope, None, None)

    router.send_http_response.assert_not_awaited()
    router.stream_reservation_consumer.assert_not_awaited()
    router.event_stream_consumer.assert_not_awaited()
    router.operation_consumer.assert_not_awaited()
    router.operation_cancellation_consumer.assert_awaited_once()
