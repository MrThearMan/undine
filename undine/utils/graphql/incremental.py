from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from graphql import ExecutionResult, GraphQLError, SubsequentIncrementalExecutionResult
from graphql.execution import CompletedResult

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
        graphql_errors_hook(result.errors)
        yield IncrementalDeliveryResponse(result=result)
        yield IncrementalDeliveryComplete()
        return

    graphql_errors_hook(result.initial_result.errors)
    yield IncrementalDeliveryResponse(result=result.initial_result)

    # Used as an ordered set, so that the pending results are completed in the order they were announced.
    pending_ids: dict[str, None] = dict.fromkeys(pending.id for pending in result.initial_result.pending)

    try:
        async for subsequent_result in result.subsequent_results:
            for pending in subsequent_result.pending or []:
                pending_ids[pending.id] = None

            for completed in subsequent_result.completed or []:
                pending_ids.pop(completed.id, None)
                graphql_errors_hook(completed.errors)

            for incremental in subsequent_result.incremental or []:
                graphql_errors_hook(incremental.errors)

            yield IncrementalDeliveryResponse(result=subsequent_result)

    # Raised when the operation is aborted, e.g. when it times out. Subsequent payloads cannot contain
    # errors for the whole operation, so the error is added to all results that are still pending.
    except GraphQLError as error:
        graphql_errors_hook([error])
        completed_results = [CompletedResult(id=pending_id, errors=[error]) for pending_id in pending_ids]
        final_result = SubsequentIncrementalExecutionResult(has_next=False, completed=completed_results)
        yield IncrementalDeliveryResponse(result=final_result)

    yield IncrementalDeliveryComplete()


async def result_to_incremental_response(  # noqa: RUF029
    result: ExecutionResult,
) -> AsyncIterator[IncrementalDeliveryResponse | IncrementalDeliveryComplete]:
    """Get iterator for a single result received from an incremental HTTP request."""
    graphql_errors_hook(result.errors)
    yield IncrementalDeliveryResponse(result=result)
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

    # Heartbeats are not part of the incremental delivery over HTTP spec, so they must never be sent
    # before the initial payload, which clients expect to be the first part of the response.
    initial_payload_sent = False

    events = aiter(event_stream)
    next_event = asyncio.ensure_future(anext(events))
    try:
        while True:
            done, _ = await asyncio.wait({next_event}, timeout=interval)
            if not done:
                if initial_payload_sent:
                    yield IncrementalDeliveryHeartbeat()
                continue

            try:
                yield next_event.result()
            except StopAsyncIteration:
                return

            initial_payload_sent = True
            next_event = asyncio.ensure_future(anext(events))

    finally:
        if not next_event.done():
            next_event.cancel()
