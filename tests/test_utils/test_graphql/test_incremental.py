from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest
from graphql import ExecutionResult, GraphQLError, version_info

from undine.dataclasses import IncrementalDeliveryComplete, IncrementalDeliveryHeartbeat, IncrementalDeliveryResponse

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(version_info < (3, 3, 0), reason="requires graphql-core>=3.3.0"),
]


async def collect(gen: AsyncIterator) -> list:
    return [item async for item in gen]


async def test_execute_graphql_incremental__execution_result(undine_settings) -> None:
    from graphql.execution.incremental_publisher import InitialIncrementalExecutionResult  # noqa: PLC0415

    from undine.utils.graphql.incremental import execute_graphql_incremental  # noqa: PLC0415

    result = ExecutionResult(data={"test": "value"})

    path = "undine.utils.graphql.incremental.execute_graphql_http_async"
    with patch(path, return_value=result):
        items = await collect(execute_graphql_incremental(params=None, request=None))  # type: ignore[arg-type]

    assert len(items) == 2
    assert isinstance(items[0], IncrementalDeliveryResponse)
    assert isinstance(items[0].result, InitialIncrementalExecutionResult)
    assert items[0].result.data == {"test": "value"}
    assert isinstance(items[1], IncrementalDeliveryComplete)


async def test_execute_graphql_incremental__incremental_results(undine_settings) -> None:
    from graphql.execution import ExperimentalIncrementalExecutionResults  # noqa: PLC0415
    from graphql.execution.incremental_publisher import (  # noqa: PLC0415
        CompletedResult,
        IncrementalDeferResult,
        InitialIncrementalExecutionResult,
        SubsequentIncrementalExecutionResult,
    )

    from undine.utils.graphql.incremental import execute_graphql_incremental  # noqa: PLC0415

    initial = InitialIncrementalExecutionResult(data={"a": 1}, pending=[], has_next=True)
    completed = CompletedResult(id="0")
    incremental = IncrementalDeferResult(data={"b": 2}, id="0")
    subsequent = SubsequentIncrementalExecutionResult(
        has_next=False,
        completed=[completed],
        incremental=[incremental],
    )

    async def fake_subsequent() -> AsyncIterator[SubsequentIncrementalExecutionResult]:  # noqa: RUF029
        yield subsequent

    incremental_results = ExperimentalIncrementalExecutionResults(
        initial_result=initial,
        subsequent_results=fake_subsequent(),
    )

    path = "undine.utils.graphql.incremental.execute_graphql_http_async"
    with patch(path, return_value=incremental_results):
        items = await collect(execute_graphql_incremental(params=None, request=None))  # type: ignore[arg-type]

    assert len(items) == 3
    assert isinstance(items[0], IncrementalDeliveryResponse)
    assert items[0].result is initial
    assert isinstance(items[1], IncrementalDeliveryResponse)
    assert items[1].result is subsequent
    assert isinstance(items[2], IncrementalDeliveryComplete)


async def test_result_to_incremental_response() -> None:
    from graphql.execution.incremental_publisher import InitialIncrementalExecutionResult  # noqa: PLC0415

    from undine.utils.graphql.incremental import result_to_incremental_response  # noqa: PLC0415

    result = ExecutionResult(data={"test": "value"}, errors=[GraphQLError("boom")])
    items = await collect(result_to_incremental_response(result))

    assert len(items) == 2
    assert isinstance(items[0], IncrementalDeliveryResponse)
    assert isinstance(items[0].result, InitialIncrementalExecutionResult)
    assert items[0].result.data == {"test": "value"}
    assert isinstance(items[1], IncrementalDeliveryComplete)


async def test_with_incremental_stream_heartbeat__no_interval(undine_settings) -> None:
    from graphql.execution.incremental_publisher import InitialIncrementalExecutionResult  # noqa: PLC0415

    from undine.utils.graphql.incremental import with_incremental_stream_heartbeat  # noqa: PLC0415

    undine_settings.INCREMENTAL_DELIVERY_HEARTBEAT_INTERVAL = 0

    async def source() -> AsyncIterator[IncrementalDeliveryResponse | IncrementalDeliveryComplete]:  # noqa: RUF029
        yield IncrementalDeliveryResponse(result=InitialIncrementalExecutionResult(data={}, pending=[], has_next=False))
        yield IncrementalDeliveryComplete()

    items = await collect(with_incremental_stream_heartbeat(source()))

    assert all(not isinstance(item, IncrementalDeliveryHeartbeat) for item in items)
    assert len(items) == 2


async def test_with_incremental_stream_heartbeat__with_interval(undine_settings) -> None:
    from graphql.execution.incremental_publisher import InitialIncrementalExecutionResult  # noqa: PLC0415

    from undine.utils.graphql.incremental import with_incremental_stream_heartbeat  # noqa: PLC0415

    undine_settings.INCREMENTAL_DELIVERY_HEARTBEAT_INTERVAL = 60

    async def source() -> AsyncIterator[IncrementalDeliveryResponse | IncrementalDeliveryComplete]:  # noqa: RUF029
        yield IncrementalDeliveryResponse(result=InitialIncrementalExecutionResult(data={}, pending=[], has_next=False))
        yield IncrementalDeliveryComplete()

    items = await collect(with_incremental_stream_heartbeat(source()))

    assert isinstance(items[0], IncrementalDeliveryHeartbeat)
    assert isinstance(items[1], IncrementalDeliveryResponse)
    assert isinstance(items[2], IncrementalDeliveryComplete)


async def test_with_incremental_stream_heartbeat__cancel_on_close(undine_settings) -> None:
    from undine.utils.graphql.incremental import with_incremental_stream_heartbeat  # noqa: PLC0415

    undine_settings.INCREMENTAL_DELIVERY_HEARTBEAT_INTERVAL = 60

    async def source() -> AsyncIterator[IncrementalDeliveryResponse | IncrementalDeliveryComplete]:
        await asyncio.sleep(100)
        yield IncrementalDeliveryComplete()

    gen = with_incremental_stream_heartbeat(source())
    first = await anext(gen)
    assert isinstance(first, IncrementalDeliveryHeartbeat)

    await gen.aclose()


async def test_with_incremental_stream_heartbeat__cancel_inside_try(undine_settings) -> None:
    from undine.utils.graphql.incremental import with_incremental_stream_heartbeat  # noqa: PLC0415

    undine_settings.INCREMENTAL_DELIVERY_HEARTBEAT_INTERVAL = 0.001

    async def source() -> AsyncIterator[IncrementalDeliveryResponse | IncrementalDeliveryComplete]:
        yield IncrementalDeliveryComplete()
        await asyncio.sleep(100)

    gen = with_incremental_stream_heartbeat(source())

    first = await anext(gen)
    assert isinstance(first, IncrementalDeliveryHeartbeat)

    second = await anext(gen)
    assert isinstance(second, IncrementalDeliveryComplete)

    third = await anext(gen)
    assert isinstance(third, IncrementalDeliveryHeartbeat)

    await gen.aclose()


async def test_with_incremental_stream_heartbeat__heartbeat_on_timeout(undine_settings) -> None:
    from undine.utils.graphql.incremental import with_incremental_stream_heartbeat  # noqa: PLC0415

    undine_settings.INCREMENTAL_DELIVERY_HEARTBEAT_INTERVAL = 0.01

    event = asyncio.Event()

    async def source() -> AsyncIterator[IncrementalDeliveryResponse | IncrementalDeliveryComplete]:
        await event.wait()
        yield IncrementalDeliveryComplete()

    async def drive() -> list:
        results = []
        async for item in with_incremental_stream_heartbeat(source()):
            results.append(item)
            if isinstance(item, IncrementalDeliveryHeartbeat) and len(results) >= 2:
                event.set()
        return results

    items = await asyncio.wait_for(drive(), timeout=5)

    heartbeats = [i for i in items if isinstance(i, IncrementalDeliveryHeartbeat)]
    assert len(heartbeats) >= 2
