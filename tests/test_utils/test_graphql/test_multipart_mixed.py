from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest
from graphql import ExecutionResult, GraphQLError

from undine.dataclasses import MultipartMixedHttpComplete, MultipartMixedHttpHeartbeat, MultipartMixedHttpResponse
from undine.exceptions import GraphQLErrorGroup
from undine.utils.graphql.multipart_mixed import (
    execute_graphql_multipart_mixed,
    result_to_multipart_mixed_response,
    with_multipart_mixed_heartbeat,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.django_db(transaction=True),
]


async def collect(gen: AsyncIterator) -> list:
    return [item async for item in gen]


async def test_execute_graphql_multipart_mixed__execution_result(undine_settings) -> None:
    result = ExecutionResult(data={"test": "value"})

    path = "undine.utils.graphql.multipart_mixed.execute_graphql_with_subscription"
    with patch(path, return_value=result):
        items = await collect(execute_graphql_multipart_mixed(params=None, request=None))  # type: ignore[arg-type]

    assert len(items) == 2
    assert isinstance(items[0], MultipartMixedHttpResponse)
    assert items[0].payload == result
    assert isinstance(items[1], MultipartMixedHttpComplete)


async def test_execute_graphql_multipart_mixed__not_async_iterator(undine_settings) -> None:
    path = "undine.utils.graphql.multipart_mixed.execute_graphql_with_subscription"
    with patch(path, return_value="unexpected"):
        items = await collect(execute_graphql_multipart_mixed(params=None, request=None))  # type: ignore[arg-type]

    assert len(items) == 2
    assert isinstance(items[0], MultipartMixedHttpResponse)
    assert items[0].payload.errors is not None
    assert isinstance(items[1], MultipartMixedHttpComplete)


async def test_execute_graphql_multipart_mixed__async_iterator__graphql_error(undine_settings) -> None:
    async def fake_stream() -> AsyncIterator[ExecutionResult]:  # noqa: RUF029
        yield ExecutionResult(data={"a": 1})
        msg = "stream error"
        raise GraphQLError(msg)

    path = "undine.utils.graphql.multipart_mixed.execute_graphql_with_subscription"
    with patch(path, return_value=fake_stream()):
        items = await collect(execute_graphql_multipart_mixed(params=None, request=None))  # type: ignore[arg-type]

    # First yield, then error response, then complete
    assert len(items) == 3
    assert isinstance(items[0], MultipartMixedHttpResponse)
    assert isinstance(items[1], MultipartMixedHttpResponse)
    assert items[1].payload.errors is not None
    assert isinstance(items[2], MultipartMixedHttpComplete)


async def test_execute_graphql_multipart_mixed__async_iterator__graphql_error_group(undine_settings) -> None:
    async def fake_stream() -> AsyncIterator[ExecutionResult]:  # noqa: RUF029
        yield ExecutionResult(data={"a": 1})
        raise GraphQLErrorGroup([GraphQLError("e1"), GraphQLError("e2")])

    path = "undine.utils.graphql.multipart_mixed.execute_graphql_with_subscription"
    with patch(path, return_value=fake_stream()):
        items = await collect(execute_graphql_multipart_mixed(params=None, request=None))  # type: ignore[arg-type]

    assert len(items) == 3
    assert isinstance(items[1], MultipartMixedHttpResponse)
    assert items[1].payload.errors is not None
    assert isinstance(items[2], MultipartMixedHttpComplete)


async def test_execute_graphql_multipart_mixed__async_iterator__generic_exception(undine_settings) -> None:
    async def fake_stream() -> AsyncIterator[ExecutionResult]:  # noqa: RUF029
        yield ExecutionResult(data={"a": 1})
        msg = "unexpected"
        raise RuntimeError(msg)

    path = "undine.utils.graphql.multipart_mixed.execute_graphql_with_subscription"
    with patch(path, return_value=fake_stream()):
        items = await collect(execute_graphql_multipart_mixed(params=None, request=None))  # type: ignore[arg-type]

    assert len(items) == 3
    assert isinstance(items[1], MultipartMixedHttpResponse)
    assert items[1].payload.errors is not None
    assert isinstance(items[2], MultipartMixedHttpComplete)


async def test_result_to_multipart_mixed_response() -> None:
    result = ExecutionResult(data={"test": "value"})
    items = await collect(result_to_multipart_mixed_response(result))

    assert len(items) == 2
    assert isinstance(items[0], MultipartMixedHttpResponse)
    assert items[0].payload == result
    assert isinstance(items[1], MultipartMixedHttpComplete)


async def test_with_multipart_mixed_heartbeat__no_interval(undine_settings) -> None:
    undine_settings.MULTIPART_MIXED_HEARTBEAT_INTERVAL = 0

    async def source() -> AsyncIterator[MultipartMixedHttpResponse | MultipartMixedHttpComplete]:  # noqa: RUF029
        yield MultipartMixedHttpResponse(payload=ExecutionResult(data={}))
        yield MultipartMixedHttpComplete()

    items = await collect(with_multipart_mixed_heartbeat(source()))

    # No heartbeats when interval is 0
    assert all(not isinstance(item, MultipartMixedHttpHeartbeat) for item in items)
    assert len(items) == 2


async def test_with_multipart_mixed_heartbeat__with_interval(undine_settings) -> None:
    undine_settings.MULTIPART_MIXED_HEARTBEAT_INTERVAL = 60

    async def source() -> AsyncIterator[MultipartMixedHttpResponse | MultipartMixedHttpComplete]:  # noqa: RUF029
        yield MultipartMixedHttpResponse(payload=ExecutionResult(data={}))
        yield MultipartMixedHttpComplete()

    items = await collect(with_multipart_mixed_heartbeat(source()))

    # Initial heartbeat is sent immediately
    assert isinstance(items[0], MultipartMixedHttpHeartbeat)
    assert isinstance(items[1], MultipartMixedHttpResponse)
    assert isinstance(items[2], MultipartMixedHttpComplete)


async def test_with_multipart_mixed_heartbeat__cancel_on_close(undine_settings) -> None:
    undine_settings.MULTIPART_MIXED_HEARTBEAT_INTERVAL = 60  # Long — ensures next_event is pending

    async def source() -> AsyncIterator[MultipartMixedHttpResponse | MultipartMixedHttpComplete]:
        await asyncio.sleep(100)  # Never completes in test
        yield MultipartMixedHttpComplete()

    gen = with_multipart_mixed_heartbeat(source())
    first = await anext(gen)
    assert isinstance(first, MultipartMixedHttpHeartbeat)  # initial heartbeat

    # Close generator while next_event is still pending — triggers finally: next_event.cancel()
    await gen.aclose()


async def test_with_multipart_mixed_heartbeat__cancel_inside_try(undine_settings) -> None:
    undine_settings.MULTIPART_MIXED_HEARTBEAT_INTERVAL = 0.001  # 1ms — fires quickly

    async def source() -> AsyncIterator[MultipartMixedHttpResponse | MultipartMixedHttpComplete]:
        yield MultipartMixedHttpComplete()
        await asyncio.sleep(100)  # Block after first event

    gen = with_multipart_mixed_heartbeat(source())

    # 1. Initial heartbeat (line 81 yield — BEFORE the try block)
    first = await anext(gen)
    assert isinstance(first, MultipartMixedHttpHeartbeat)

    # 2. Resume into try block; next_event fires (source yields complete event)
    second = await anext(gen)
    assert isinstance(second, MultipartMixedHttpComplete)

    # 3. Generator creates NEW next_event (waiting for source's 2nd yield = sleep 100s),
    #    then asyncio.wait times out (1ms) → yields a timeout heartbeat.
    #    Generator is now suspended at line 89 inside the try block.
    third = await anext(gen)
    assert isinstance(third, MultipartMixedHttpHeartbeat)

    # 4. Close while generator is suspended inside the try block with a pending next_event.
    #    GeneratorExit propagates to the finally block → next_event.cancel() at line 101.
    await gen.aclose()


async def test_with_multipart_mixed_heartbeat__heartbeat_on_timeout(undine_settings) -> None:
    undine_settings.MULTIPART_MIXED_HEARTBEAT_INTERVAL = 0.01  # 10ms

    event = asyncio.Event()

    async def source() -> AsyncIterator[MultipartMixedHttpResponse | MultipartMixedHttpComplete]:
        await event.wait()
        yield MultipartMixedHttpComplete()

    async def drive() -> list:
        results = []
        async for item in with_multipart_mixed_heartbeat(source()):
            results.append(item)
            if isinstance(item, MultipartMixedHttpHeartbeat) and len(results) >= 2:
                # Got at least one timeout heartbeat, release the stream
                event.set()
        return results

    items = await asyncio.wait_for(drive(), timeout=5)

    heartbeats = [i for i in items if isinstance(i, MultipartMixedHttpHeartbeat)]
    assert len(heartbeats) >= 2  # initial + at least one timeout
