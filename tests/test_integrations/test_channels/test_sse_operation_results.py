from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from http import HTTPStatus

import pytest

from tests.helpers import TEST_WAIT_TIME
from tests.test_integrations.test_channels.helpers import (
    create_mutation_schema,
    create_query_schema,
    make_sse_get_operation_communicator,
    open_sse_stream,
    read_sse_complete_event,
    read_sse_next_event,
    sse_get_response,
    sse_read_stream_event,
    sse_send_request,
    submit_sse_operation,
)
from undine import Entrypoint, RootType, create_schema
from undine.typing import GQLInfo

pytestmark = [
    pytest.mark.django_db(transaction=True),
]


async def test_channels__sse__query_result_on_stream(undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_SSE = True
    undine_settings.SCHEMA = create_query_schema()

    stream = await open_sse_stream()
    operation_id = "op-q"
    await submit_sse_operation(stream, query="query { test }", operation_id=operation_id)

    payload = await read_sse_next_event(stream, operation_id=operation_id)
    assert payload == {"data": {"test": "Hello, World!"}}

    await read_sse_complete_event(stream, operation_id=operation_id)

    await asyncio.sleep(TEST_WAIT_TIME)


async def test_channels__sse__get_operation_submit(undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_SSE = True
    undine_settings.SCHEMA = create_query_schema()

    stream = await open_sse_stream()
    operation_id = "op-get"

    op_communicator = make_sse_get_operation_communicator(
        user=stream.user,
        session=stream.session,
        token=stream.token,
        query="query { test }",
        operation_id=operation_id,
    )
    await sse_send_request(op_communicator)
    op_response = await sse_get_response(op_communicator)
    assert op_response["status"] == HTTPStatus.ACCEPTED

    payload = await read_sse_next_event(stream, operation_id=operation_id)
    assert payload == {"data": {"test": "Hello, World!"}}

    await read_sse_complete_event(stream, operation_id=operation_id)

    await asyncio.sleep(TEST_WAIT_TIME)


async def test_channels__sse__mutation_over_sse(undine_settings) -> None:
    undine_settings.ALLOW_MUTATIONS_WITH_SSE = True
    undine_settings.SCHEMA = create_mutation_schema()

    stream = await open_sse_stream()
    operation_id = "op-mut"
    await submit_sse_operation(stream, query="mutation { doSomething }", operation_id=operation_id)

    payload = await read_sse_next_event(stream, operation_id=operation_id)
    assert payload == {"data": {"doSomething": "done"}}

    await read_sse_complete_event(stream, operation_id=operation_id)

    await asyncio.sleep(TEST_WAIT_TIME)


async def test_channels__sse__subscription_streaming(undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def placeholder(self) -> str:
            return ""

    class Subscription(RootType, schema_name="Subscription"):
        @Entrypoint
        async def counter(self, info: GQLInfo) -> AsyncIterator[int]:
            for i in range(3):
                yield i

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    stream = await open_sse_stream()
    operation_id = "op-sub"
    await submit_sse_operation(stream, query="subscription { counter }", operation_id=operation_id)

    for expected_value in range(3):
        payload = await read_sse_next_event(stream, operation_id=operation_id)
        assert payload == {"data": {"counter": expected_value}}

    await read_sse_complete_event(stream, operation_id=operation_id)

    await asyncio.sleep(TEST_WAIT_TIME)


async def test_channels__sse__subscription_with_variables(undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def placeholder(self) -> str:
            return ""

    class Subscription(RootType, schema_name="Subscription"):
        @Entrypoint
        async def prefixed_counter(self, info: GQLInfo, *, prefix: str) -> AsyncIterator[str]:
            for i in range(3):
                yield f"{prefix}-{i}"

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    stream = await open_sse_stream()
    operation_id = "op-vars"
    await submit_sse_operation(
        stream,
        query="subscription($prefix: String!) { prefixedCounter(prefix: $prefix) }",
        operation_id=operation_id,
        variables={"prefix": "test"},
    )

    for expected_value in range(3):
        payload = await read_sse_next_event(stream, operation_id=operation_id)
        assert payload == {"data": {"prefixedCounter": f"test-{expected_value}"}}

    await read_sse_complete_event(stream, operation_id=operation_id)

    await asyncio.sleep(TEST_WAIT_TIME)


async def test_channels__sse__concurrent_operations(undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_SSE = True
    undine_settings.SCHEMA = create_query_schema()

    stream = await open_sse_stream()
    await submit_sse_operation(stream, query="query { test }", operation_id="op-1")
    await submit_sse_operation(stream, query="query { test }", operation_id="op-2")

    received_events: dict[str, list[str]] = {"op-1": [], "op-2": []}
    for _ in range(4):
        event = await sse_read_stream_event(stream.communicator)
        received_events[event["data"]["id"]].append(event["event"])

    assert received_events["op-1"] == ["next", "complete"]
    assert received_events["op-2"] == ["next", "complete"]

    await asyncio.sleep(TEST_WAIT_TIME)
