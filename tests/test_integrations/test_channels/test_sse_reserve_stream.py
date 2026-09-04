from __future__ import annotations

import uuid
from http import HTTPStatus

import pytest
from django.contrib.auth.models import AnonymousUser

from tests.test_integrations.test_channels.helpers import (
    _create_session,
    _create_user,
    _reserve_stream,
    make_sse_communicator,
    session_aget,
    session_aload,
    session_asave,
    session_aset,
    sse_get_response,
    sse_send_request,
)
from undine.typing import SSEState
from undine.utils.graphql.server_sent_events import (
    get_sse_operation_key,
    get_sse_stream_state_key,
    get_sse_stream_token_key,
)

pytestmark = [
    pytest.mark.django_db(transaction=True),
]


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

    stream_token = await session_aget(session, get_sse_stream_token_key())
    stream_state = await session_aget(session, get_sse_stream_state_key())
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

    stream_token = await session_aget(session, get_sse_stream_token_key())
    stream_state = await session_aget(session, get_sse_stream_state_key())
    assert stream_state == SSEState.REGISTERED
    assert stream_token == new_token


async def test_channels__sse__reserve_stream__stale_opened_state(undine_settings) -> None:
    user = await _create_user()
    session = await _create_session(user)

    # Simulate stale OPENED state left in the session (e.g. from a race condition on disconnect)
    await session_aset(session, get_sse_stream_token_key(), "stale-token")
    await session_aset(session, get_sse_stream_state_key(), SSEState.OPENED)
    await session_asave(session)

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
    assert await session_aget(session, stream_operation_key) is None

    # Verify new stream state
    stream_token = await session_aget(session, get_sse_stream_token_key())
    stream_state = await session_aget(session, get_sse_stream_state_key())
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
    await session_aset(session, operation_key, "ok")
    await session_asave(session)

    # Re-reserving from REGISTERED state should clean up stale operations
    new_token = await _reserve_stream(user, session)
    assert new_token != token

    await session_aload(session)
    assert await session_aget(session, operation_key) is None
