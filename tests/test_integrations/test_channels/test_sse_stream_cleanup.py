from __future__ import annotations

import asyncio

import pytest

from tests.helpers import TEST_WAIT_TIME
from tests.test_integrations.test_channels.helpers import (
    _reserve_stream,
    cancel_sse_operation,
    create_slow_subscription_schema,
    disconnect_sse_stream,
    open_sse_stream,
    read_sse_complete_event,
    read_sse_next_event,
    session_aget,
    session_aload,
    submit_sse_operation,
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


async def test_channels__sse__cancel_running_subscription(undine_settings) -> None:
    undine_settings.SCHEMA = create_slow_subscription_schema()

    stream = await open_sse_stream()
    operation_id = "op-cancel"
    await submit_sse_operation(stream, query="subscription { slow }", operation_id=operation_id)

    first_payload = await read_sse_next_event(stream, operation_id=operation_id)
    assert first_payload == {"data": {"slow": "first"}}

    await cancel_sse_operation(stream, operation_id=operation_id)

    await read_sse_complete_event(stream, operation_id=operation_id)

    await asyncio.sleep(TEST_WAIT_TIME)
    await session_aload(stream.session)
    assert await session_aget(stream.session, get_sse_operation_key(operation_id=operation_id)) is None


async def test_channels__sse__disconnect_cancels_operation(undine_settings) -> None:
    undine_settings.SCHEMA = create_slow_subscription_schema()

    stream = await open_sse_stream()
    operation_id = "op-dc"
    await submit_sse_operation(stream, query="subscription { slow }", operation_id=operation_id)

    first_payload = await read_sse_next_event(stream, operation_id=operation_id)
    assert first_payload == {"data": {"slow": "first"}}

    operation_key = get_sse_operation_key(operation_id=operation_id)
    await session_aload(stream.session)
    assert await session_aget(stream.session, operation_key) is not None

    await disconnect_sse_stream(stream)

    await session_aload(stream.session)
    assert await session_aget(stream.session, operation_key) is None
    assert await session_aget(stream.session, get_sse_stream_state_key()) is None
    assert await session_aget(stream.session, get_sse_stream_token_key()) is None


async def test_channels__sse__disconnect_cancels_multiple_operations(undine_settings) -> None:
    undine_settings.SCHEMA = create_slow_subscription_schema()

    stream = await open_sse_stream()
    operation_ids = ["op-dc-1", "op-dc-2"]
    for operation_id in operation_ids:
        await submit_sse_operation(stream, query="subscription { slow }", operation_id=operation_id)
        first_payload = await read_sse_next_event(stream, operation_id=operation_id)
        assert first_payload == {"data": {"slow": "first"}}

    await disconnect_sse_stream(stream)

    await session_aload(stream.session)
    assert await session_aget(stream.session, get_sse_stream_state_key()) is None
    assert await session_aget(stream.session, get_sse_stream_token_key()) is None
    for operation_id in operation_ids:
        assert await session_aget(stream.session, get_sse_operation_key(operation_id=operation_id)) is None


async def test_channels__sse__re_reserve_cancels_operation(undine_settings) -> None:
    undine_settings.SCHEMA = create_slow_subscription_schema()

    stream = await open_sse_stream()
    operation_id = "op-re"
    await submit_sse_operation(stream, query="subscription { slow }", operation_id=operation_id)

    first_payload = await read_sse_next_event(stream, operation_id=operation_id)
    assert first_payload == {"data": {"slow": "first"}}

    new_token = await _reserve_stream(stream.user, stream.session)
    assert new_token != stream.token

    await asyncio.sleep(TEST_WAIT_TIME)

    await session_aload(stream.session)
    assert await session_aget(stream.session, get_sse_operation_key(operation_id=operation_id)) is None
    assert await session_aget(stream.session, get_sse_stream_state_key()) == SSEState.REGISTERED


async def test_channels__sse__re_reserve_cancels_multiple_operations(undine_settings) -> None:
    undine_settings.SCHEMA = create_slow_subscription_schema()

    stream = await open_sse_stream()
    operation_ids = ["op-re-1", "op-re-2"]
    for operation_id in operation_ids:
        await submit_sse_operation(stream, query="subscription { slow }", operation_id=operation_id)
        first_payload = await read_sse_next_event(stream, operation_id=operation_id)
        assert first_payload == {"data": {"slow": "first"}}

    new_token = await _reserve_stream(stream.user, stream.session)
    assert new_token != stream.token

    await asyncio.sleep(TEST_WAIT_TIME)

    await session_aload(stream.session)
    for operation_id in operation_ids:
        assert await session_aget(stream.session, get_sse_operation_key(operation_id=operation_id)) is None
    assert await session_aget(stream.session, get_sse_stream_state_key()) == SSEState.REGISTERED
