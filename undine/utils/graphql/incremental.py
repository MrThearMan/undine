from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from graphql import ExecutionResult, InitialIncrementalExecutionResult  # type: ignore[attr-defined]

from undine.dataclasses import IncrementalDeliveryComplete, IncrementalDeliveryHeartbeat, IncrementalDeliveryResponse
from undine.execution import execute_graphql_http_async
from undine.settings import undine_settings
from undine.utils.graphql.utils import graphql_errors_hook

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol

__all__ = [
    "execute_graphql_incremental",
    "result_to_incremental_response",
    "with_incremental_stream_heartbeat",
]


async def execute_graphql_incremental(
    params: GraphQLHttpParams,
    request: DjangoRequestProtocol,
) -> AsyncIterator[IncrementalDeliveryResponse | IncrementalDeliveryComplete]:
    """Execute a GraphQL operation received through an incremental HTTP request."""
    result = await execute_graphql_http_async(params, request)

    if isinstance(result, ExecutionResult):
        initial_result = execution_result_to_initial_incremental_response(result)
        yield IncrementalDeliveryResponse(result=initial_result)
        yield IncrementalDeliveryComplete()
        return

    graphql_errors_hook(result.initial_result.errors)
    yield IncrementalDeliveryResponse(result=result.initial_result)

    async for subsequent_result in result.subsequent_results:
        for completed in subsequent_result.completed or []:
            graphql_errors_hook(completed.errors)

        for incremental in subsequent_result.incremental or []:
            graphql_errors_hook(incremental.errors)

        yield IncrementalDeliveryResponse(result=subsequent_result)

    yield IncrementalDeliveryComplete()


async def result_to_incremental_response(  # noqa: RUF029
    result: ExecutionResult,
) -> AsyncIterator[IncrementalDeliveryResponse | IncrementalDeliveryComplete]:
    """Get iterator for a single result received from an incremental HTTP request."""
    initial_result = execution_result_to_initial_incremental_response(result)
    yield IncrementalDeliveryResponse(result=initial_result)
    yield IncrementalDeliveryComplete()


async def with_incremental_stream_heartbeat(
    event_stream: AsyncIterator[IncrementalDeliveryResponse | IncrementalDeliveryComplete],
) -> AsyncIterator[IncrementalDeliveryResponse | IncrementalDeliveryComplete | IncrementalDeliveryHeartbeat]:
    """Wrap an event stream to periodically emit incremental delivery over HTTP heartbeats."""
    interval = undine_settings.INCREMENTAL_DELIVERY_HEARTBEAT_INTERVAL
    if not interval:
        async for event in event_stream:
            yield event
        return

    yield IncrementalDeliveryHeartbeat()

    events = aiter(event_stream)
    next_event = asyncio.ensure_future(anext(events))
    try:
        while True:
            done, _ = await asyncio.wait({next_event}, timeout=interval)
            if not done:
                yield IncrementalDeliveryHeartbeat()
                continue

            try:
                yield next_event.result()
            except StopAsyncIteration:
                return

            next_event = asyncio.ensure_future(anext(events))

    finally:
        if not next_event.done():
            next_event.cancel()


def execution_result_to_initial_incremental_response(result: ExecutionResult) -> InitialIncrementalExecutionResult:
    return InitialIncrementalExecutionResult(
        data=result.data,
        errors=graphql_errors_hook(result.errors),
        pending=[],
        has_next=False,
        extensions=result.extensions,
    )
