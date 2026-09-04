from __future__ import annotations

import asyncio
from http import HTTPStatus

import pytest
from django.contrib.auth.models import AnonymousUser

from tests.helpers import TEST_WAIT_TIME
from tests.test_integrations.test_channels.helpers import (
    _create_session,
    _create_user,
    _open_stream,
    _reserve_stream,
    create_query_schema,
    make_operation_body,
    make_sse_cancel_communicator,
    make_sse_communicator,
    make_sse_operation_communicator,
    session_aget,
    session_aload,
    sse_get_response,
    sse_read_stream_event,
    sse_send_request,
)
from undine import Entrypoint, RootType, create_schema
from undine.utils.graphql.server_sent_events import get_sse_operation_key

pytestmark = [
    pytest.mark.django_db(transaction=True),
]


async def test_channels__sse__cancel_subscription() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    communicator = make_sse_cancel_communicator(
        user=user,
        session=session,
        token=token,
        operation_id="op-1",
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.OK


async def test_channels__sse__cancel_subscription__token_via_query_param() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    communicator = make_sse_communicator(
        method="DELETE",
        query_string=f"token={token}&operationId=op-1".encode(),
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

    communicator = make_sse_cancel_communicator(
        user=user,
        session=session,
        token=token,
        operation_id="nonexistent",
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    # cancel_operation sends to the group but there's no consumer listening,
    # so it just succeeds silently
    assert response["status"] == HTTPStatus.OK


async def test_channels__sse__cancel_subscription__stream_not_registered() -> None:
    user = await _create_user()
    session = await _create_session(user)

    communicator = make_sse_cancel_communicator(
        user=user,
        session=session,
        token="nonexistent-token",
        operation_id="op-1",
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.NOT_FOUND
    assert response["json"]["errors"][0]["message"] == "Stream not found"


async def test_channels__sse__cancel_subscription__stream_not_opened() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)

    communicator = make_sse_cancel_communicator(
        user=user,
        session=session,
        token=token,
        operation_id="op-1",
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    # The spec allows cancellation before the stream is actually opened.
    # Targets the operation's own channel group, independent of stream state.
    assert response["status"] == HTTPStatus.OK


async def test_channels__sse__cancel_subscription__before_stream_opened(undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_SSE = True
    undine_settings.SCHEMA = create_query_schema()

    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    operation_id = "op-1"

    # Submit operation (queued, waiting for stream to open)
    op_communicator = make_sse_operation_communicator(user=user, session=session, token=token)
    body = make_operation_body(query="query { test }", operation_id=operation_id)
    await sse_send_request(op_communicator, body=body)

    # Let the operation consumer complete handle() — it needs multiple
    # yields for session save and channel group joins.
    await asyncio.sleep(TEST_WAIT_TIME)

    # Cancel the queued operation
    cancel_communicator = make_sse_cancel_communicator(
        user=user,
        session=session,
        token=token,
        operation_id=operation_id,
    )
    await sse_send_request(cancel_communicator)
    cancel_response = await sse_get_response(cancel_communicator)
    assert cancel_response["status"] == HTTPStatus.OK

    # Let the cancel signal propagate through the channel layer and
    # the operation consumer's dispatch loop (needs multiple yields).
    await asyncio.sleep(TEST_WAIT_TIME)

    # The operation never reaches the stream, so the client gets a 204 instead of a 202.
    op_response = await sse_get_response(op_communicator)
    assert op_response["status"] == HTTPStatus.NO_CONTENT

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
    await session_aload(session)
    assert await session_aget(session, get_sse_operation_key(operation_id=operation_id)) is None


async def test_channels__sse__cancel_subscription__wrong_stream_token() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    communicator = make_sse_cancel_communicator(
        user=user,
        session=session,
        token="wrong-token",
        operation_id="op-1",
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


async def test_channels__sse__cancel_subscription__after_accept(undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_SSE = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    stream_communicator = await _open_stream(user, session, token)

    operation_id = "op-584"
    op_communicator = make_sse_operation_communicator(user=user, session=session, token=token)
    body = make_operation_body(query="query { test }", operation_id=operation_id)
    await sse_send_request(op_communicator, body=body)

    op_response = await sse_get_response(op_communicator)
    assert op_response["status"] == HTTPStatus.ACCEPTED

    # Consume the events on the stream
    next_event = await sse_read_stream_event(stream_communicator)
    assert next_event["event"] == "next"

    complete_event = await sse_read_stream_event(stream_communicator)
    assert complete_event["event"] == "complete"

    await asyncio.sleep(TEST_WAIT_TIME)
