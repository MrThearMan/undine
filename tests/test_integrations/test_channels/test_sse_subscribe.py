from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from http import HTTPStatus
from typing import NamedTuple
from unittest.mock import AsyncMock, MagicMock

import pytest
from channels.exceptions import StopConsumer
from django.conf import settings as django_settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import caches

from tests.helpers import TEST_WAIT_TIME, parametrize_helper
from tests.test_integrations.test_channels.helpers import (
    _create_session,
    _create_user,
    _open_stream,
    _reserve_stream,
    create_query_schema,
    make_http_scope,
    make_operation_body,
    make_sse_communicator,
    make_sse_operation_communicator,
    open_sse_stream,
    read_sse_complete_event,
    read_sse_next_event,
    session_aget,
    session_aload,
    session_asave,
    session_aset,
    sse_get_response,
    sse_send_request,
)
from undine import Entrypoint, RootType, create_schema
from undine.dataclasses import GraphQLHttpParams
from undine.integrations.channels import SSEOperationConsumer
from undine.typing import SSEOperationCancelEvent, SSEStreamOpenEvent
from undine.utils.graphql.server_sent_events import get_sse_operation_claim_key, get_sse_operation_key

pytestmark = [
    pytest.mark.django_db(transaction=True),
]


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

    communicator = make_sse_operation_communicator(user=user, session=session, token=token)
    body = make_operation_body(query="query { test }", operation_id="op-1")
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.ACCEPTED

    # Wait for the operation task to finalize (which saves the session) before teardown.
    await asyncio.sleep(TEST_WAIT_TIME)


async def test_channels__sse__subscribe__unauthenticated() -> None:
    session = await _create_session()

    body = make_operation_body(query="subscription { test }", operation_id="op-1")

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

    body = make_operation_body(query="subscription { test }", operation_id="op-1")

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

    communicator = make_sse_operation_communicator(user=user, session=session, token=token)
    body = make_operation_body(query="subscription { test }", operation_id=operation_id)
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    # The operation waits for the stream to open before responding.
    # If the stream never opens, the client gets a 409 instead of 202.
    assert response["status"] == HTTPStatus.CONFLICT
    assert response["json"]["errors"][0]["message"] == "Operation timed out before stream was opened"

    # Let the operation cleanup (finally block) finish before checking session.
    await asyncio.sleep(TEST_WAIT_TIME)

    # Operation should not be saved in the session since it was rejected.
    operation_key = get_sse_operation_key(operation_id=operation_id)
    await session_aload(session)
    assert await session_aget(session, operation_key) is None


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

    op_communicator = make_sse_operation_communicator(user=user, session=session, token=token)
    body = make_operation_body(query="query { test }", operation_id="op-1")
    # The POST waits for the stream to open before responding with 202,
    # so send it first, then open the stream concurrently.
    await sse_send_request(op_communicator, body=body)

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

    # Consume the complete event so the operation task can run to completion
    # (including 'finalize_operation', which saves the session) before teardown.
    complete_event = await stream_communicator.receive_output(timeout=5)
    assert complete_event["type"] == "http.response.body"
    assert b"event: complete" in complete_event["body"]

    await asyncio.sleep(TEST_WAIT_TIME)


async def test_channels__sse__subscribe__wrong_stream_token() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    body = make_operation_body(query="subscription { test }", operation_id="op-1")

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

    body = make_operation_body(query="subscription { test }", operation_id="op-1")

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


class OperationIdMissingParams(NamedTuple):
    body: bytes


@pytest.mark.parametrize(
    **parametrize_helper({
        "no extensions": OperationIdMissingParams(
            body=json.dumps({"query": "subscription { test }"}).encode(),
        ),
        "empty extensions": OperationIdMissingParams(
            body=json.dumps({"query": "subscription { test }", "extensions": {}}).encode(),
        ),
        "empty operation id": OperationIdMissingParams(
            body=make_operation_body(query="subscription { test }", operation_id=""),
        ),
    })
)
async def test_channels__sse__subscribe__operation_id_missing(body) -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    communicator = make_sse_operation_communicator(user=user, session=session, token=token)
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.BAD_REQUEST
    assert response["json"]["errors"][0]["message"] == "Operation ID is missing"


async def test_channels__sse__subscribe__non_string_operation_id(undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_SSE = True
    undine_settings.SCHEMA = create_query_schema()

    stream = await open_sse_stream()
    body = json.dumps({"query": "query { test }", "extensions": {"operationId": 1}}).encode()

    op_communicator = make_sse_operation_communicator(
        user=stream.user,
        session=stream.session,
        token=stream.token,
    )
    await sse_send_request(op_communicator, body=body)
    op_response = await sse_get_response(op_communicator)
    assert op_response["status"] == HTTPStatus.ACCEPTED

    payload = await read_sse_next_event(stream, operation_id="1")
    assert payload == {"data": {"test": "Hello, World!"}}

    await read_sse_complete_event(stream, operation_id="1")

    await asyncio.sleep(TEST_WAIT_TIME)


async def test_channels__sse__subscribe__operation_already_exists(undine_settings) -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    operation_id = "op-1"

    # Mark operation as already existing in session
    operation_key = get_sse_operation_key(operation_id=operation_id)
    await session_aset(session, operation_key, "ok")
    await session_asave(session)

    communicator = make_sse_operation_communicator(user=user, session=session, token=token)
    body = make_operation_body(query="subscription { test }", operation_id=operation_id)
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

    communicator = make_sse_operation_communicator(user=user, session=session, token=token)
    body = make_operation_body(query="subscription { test }", operation_id=operation_id)
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

    communicator = make_sse_operation_communicator(user=user, session=session, token=token)
    body = make_operation_body(query="query { test }", operation_id=operation_id)
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)
    assert response["status"] == HTTPStatus.ACCEPTED

    # Cache claim should already be released once the session contains the operation.
    cache = caches[django_settings.SESSION_CACHE_ALIAS]
    cache_key = get_sse_operation_claim_key(token, operation_id)
    assert await cache.aget(cache_key) is None

    # Wait for the operation task to finalize (which saves the session) before teardown.
    await asyncio.sleep(TEST_WAIT_TIME)


async def test_channels__sse__subscribe__sse_stream_open() -> None:
    consumer = SSEOperationConsumer()
    consumer._stream_opened = asyncio.Event()

    event = SSEStreamOpenEvent(type="sse.stream.open")
    await consumer.sse_stream_open(event)

    assert consumer._stream_opened.is_set()


async def test_channels__sse__subscribe__sse_stream_open__already_open() -> None:
    consumer = SSEOperationConsumer()
    consumer._stream_opened = asyncio.Event()
    consumer._stream_opened.set()  # already set

    event = SSEStreamOpenEvent(type="sse.stream.open")
    await consumer.sse_stream_open(event)

    # Should still be set (no error, no-op effectively)
    assert consumer._stream_opened.is_set()


async def test_channels__sse__subscribe__operation_consumer_disconnect_with_token() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    communicator = make_sse_operation_communicator(user=user, session=session, token=token)
    body = make_operation_body(query="subscription { nonexistent }", operation_id="op-dc")

    # Send the request but force a disconnect immediately
    await communicator.send_input({"type": "http.request", "body": body, "more_body": False})

    await asyncio.sleep(TEST_WAIT_TIME)

    # Send http.disconnect to trigger disconnect() in the consumer
    await communicator.send_input({"type": "http.disconnect"})
    await asyncio.sleep(TEST_WAIT_TIME)


async def test_channels__sse__subscribe__dispatch_loop_channel_task_done_covers_wait_for_branch() -> None:
    consumer = SSEOperationConsumer()
    consumer._stream_opened = asyncio.Event()
    consumer.base_send = AsyncMock()
    consumer.scope = make_http_scope(headers=[(b"x-graphql-event-stream-token", b"test-token")])  # type: ignore[arg-type]
    consumer.messages = []
    consumer.handler = MagicMock()
    consumer.handler.disconnect_operation = AsyncMock()

    # An operation task that completes immediately.
    async def instant_operation() -> None:
        pass

    consumer.operation = asyncio.create_task(instant_operation())
    # Let the event loop run so the operation task is already done.
    await asyncio.sleep(0)

    loop = asyncio.get_event_loop()

    def make_done_future() -> asyncio.Future:
        future: asyncio.Future = loop.create_future()
        future.set_result(SSEOperationCancelEvent(type="sse.operation.cancel"))
        return future

    consumer.channel_receive = make_done_future  # type: ignore[method-assign]

    async def blocking_receive() -> None:
        await asyncio.sleep(100)

    # dispatch_loop exits via StopConsumer when the already-done operation is detected.
    with suppress(StopConsumer):
        await consumer.dispatch_loop(blocking_receive)

    # The operation task is still done (not re-cancelled).
    assert consumer.operation.done()


async def test_channels__sse__subscribe__disconnect_cancels_pending_operation() -> None:
    consumer = SSEOperationConsumer()
    consumer.scope = make_http_scope(headers=[(b"x-graphql-event-stream-token", b"test-token")])  # type: ignore[arg-type]
    consumer.messages = []
    consumer.handler = MagicMock()
    consumer.handler.disconnect_operation = AsyncMock()
    consumer.base_send = AsyncMock()

    async def slow_operation() -> None:
        await asyncio.sleep(100)

    consumer.operation = asyncio.create_task(slow_operation())
    assert not consumer.operation.done()

    await consumer.disconnect()

    assert consumer.operation.done()
    assert consumer.operation.cancelled()


async def test_channels__sse__subscribe__execute_on_stream_open__cancelled_after_accept() -> None:
    consumer = SSEOperationConsumer()
    consumer._stream_opened = asyncio.Event()
    consumer._stream_opened.set()
    consumer.base_send = AsyncMock()
    consumer.scope = make_http_scope()  # type: ignore[arg-type]
    consumer.messages = []
    consumer.handler = MagicMock()
    consumer.handler.execute_operation = AsyncMock(side_effect=asyncio.CancelledError())
    consumer.handler.finalize_operation = AsyncMock()

    params = GraphQLHttpParams(document="query { test }", variables={}, operation_name=None, extensions={})

    await consumer.execute_on_stream_open("test-token", "op-1", params)

    # finalize_operation must always run (finally block).
    consumer.handler.finalize_operation.assert_awaited_once_with("test-token", "op-1")
    # Only two base_send calls for the 202 ACCEPTED response; no 204 response.
    assert consumer.base_send.call_count == 2


async def test_channels__sse__subscribe__sse_operation_cancel__when_operation_none() -> None:
    consumer = SSEOperationConsumer()
    consumer.operation = None

    event = SSEOperationCancelEvent(type="sse.operation.cancel")
    await consumer.sse_operation_cancel(event)

    assert consumer.operation is None


async def test_channels__sse__subscribe__sse_operation_cancel__when_operation_already_done() -> None:
    consumer = SSEOperationConsumer()

    async def instant_operation() -> None:
        pass

    consumer.operation = asyncio.create_task(instant_operation())
    await asyncio.sleep(0)
    assert consumer.operation.done()

    event = SSEOperationCancelEvent(type="sse.operation.cancel")
    await consumer.sse_operation_cancel(event)

    # Still done, not re-cancelled.
    assert consumer.operation.done()


async def test_channels__sse__subscribe__dispatch_loop_receive_task_done_covers_wait_for_branch() -> None:
    consumer = SSEOperationConsumer()
    consumer._stream_opened = asyncio.Event()
    consumer.base_send = AsyncMock()
    consumer.scope = make_http_scope(headers=[(b"x-graphql-event-stream-token", b"test-token")])  # type: ignore[arg-type]
    consumer.messages = []
    consumer.handler = MagicMock()
    consumer.handler.disconnect_operation = AsyncMock()

    # Operation task remains running until we signal it, keeping the loop past iter 1.
    op_complete = asyncio.Event()

    async def operation_task() -> None:
        await op_complete.wait()

    consumer.operation = asyncio.create_task(operation_task())

    # receive returns immediately once; subsequent calls block.
    receive_call_count = 0

    async def receive() -> dict:
        nonlocal receive_call_count
        receive_call_count += 1
        if receive_call_count == 1:
            return {"type": "http.disconnect"}
        await asyncio.sleep(100)
        return {"type": "http.disconnect"}

    # channel_receive always blocks so the loop waits for receive_task or the operation.
    async def blocking_channel_receive() -> dict:
        await asyncio.sleep(100)
        return {}

    consumer.channel_receive = blocking_channel_receive  # type: ignore[method-assign]

    async def finish_operation() -> None:
        # Wait long enough for at least two dispatch_loop iterations to run,
        # ensuring line 507 evaluates `receive_task.done()` as True.
        await asyncio.sleep(0.05)
        op_complete.set()

    finisher = asyncio.create_task(finish_operation())

    with suppress(StopConsumer):
        await consumer.dispatch_loop(receive)

    await finisher
    assert consumer.operation.done()
