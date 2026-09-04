from __future__ import annotations

import asyncio
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock

import pytest
from django.conf import settings as django_settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import caches

from tests.helpers import TEST_WAIT_TIME
from tests.test_integrations.test_channels.helpers import (
    _create_session,
    _create_user,
    _open_stream,
    _reserve_stream,
    make_http_scope,
    make_sse_communicator,
    session_aget,
    sse_get_response,
    sse_send_request,
)
from undine.integrations.channels import SSEEventStreamConsumer
from undine.typing import SSEOperationResultEvent, SSEState
from undine.utils.graphql.server_sent_events import (
    get_sse_stream_claim_key,
    get_sse_stream_state_key,
    get_sse_stream_token_key,
)

pytestmark = [
    pytest.mark.django_db(transaction=True),
]


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
    assert headers["Content-Type"] == "text/event-stream; charset=utf-8"
    assert headers["Connection"] == "keep-alive"
    assert headers["Cache-Control"] == "no-cache, no-store, must-revalidate"

    # First body event (SSE comment keep-alive, keeps connection open)
    body_event = await communicator.receive_output(timeout=3)
    assert body_event["type"] == "http.response.body"
    assert body_event["body"] == b":\n\n"
    assert body_event.get("more_body") is True

    stream_token = await session_aget(session, get_sse_stream_token_key())
    stream_state = await session_aget(session, get_sse_stream_state_key())
    assert stream_state == SSEState.OPENED
    assert stream_token == token


async def test_channels__sse__get_stream__token_via_header() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)

    communicator = make_sse_communicator(
        method="GET",
        headers=[
            (b"accept", b"text/event-stream"),
            (b"x-graphql-event-stream-token", token.encode()),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator)

    start = await communicator.receive_output(timeout=3)
    assert start["type"] == "http.response.start"
    assert start["status"] == HTTPStatus.OK

    headers = {k.decode(): v.decode() for k, v in start.get("headers", [])}
    assert headers["Content-Type"] == "text/event-stream; charset=utf-8"

    body_event = await communicator.receive_output(timeout=3)
    assert body_event["type"] == "http.response.body"
    assert body_event["body"] == b":\n\n"
    assert body_event.get("more_body") is True


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


async def test_channels__sse__get_stream__event_stream_disconnect_before_open() -> None:
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

    # Send a disconnect before the stream body is sent (force http.disconnect)
    await communicator.send_input({"type": "http.disconnect"})

    # The consumer should handle the disconnect gracefully
    # without trying to send the close body (since `_stream_opened` may be False)
    await asyncio.sleep(TEST_WAIT_TIME)


async def test_channels__sse__get_stream__operation_event_stream_not_opened() -> None:
    consumer = SSEEventStreamConsumer()
    consumer._stream_opened = False
    consumer.base_send = AsyncMock()

    event = SSEOperationResultEvent(type="sse.operation.event", event="data: test\n\n")
    await consumer.sse_operation_event(event)

    # `base_send` should not have been called since stream is not opened
    consumer.base_send.assert_not_awaited()


async def test_channels__sse__get_stream__disconnect_before_stream_opened() -> None:
    consumer = SSEEventStreamConsumer()
    consumer._stream_opened = False
    consumer.scope = make_http_scope(query_string=b"token=test-token")  # type: ignore[arg-type]
    consumer.messages = []
    consumer.handler = MagicMock()
    consumer.handler.disconnect_stream = AsyncMock()
    consumer.base_send = AsyncMock()

    await consumer.disconnect()

    consumer.handler.disconnect_stream.assert_awaited_once_with("test-token")
    consumer.base_send.assert_not_awaited()
