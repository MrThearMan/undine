from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from graphql import GraphQLError

from undine.dataclasses import CompletedEventDC, KeepAliveSignalDC, NextEventDC
from undine.exceptions import GraphQLErrorGroup, GraphQLUnexpectedError
from undine.execution import execute_graphql_with_subscription
from undine.settings import undine_settings
from undine.utils.graphql.utils import get_error_execution_result

if TYPE_CHECKING:
    from graphql import ExecutionResult

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol

__all__ = [
    "execute_graphql_sse_dc",
    "result_to_sse_dc",
    "with_keep_alive_dc",
]


async def execute_graphql_sse_dc(
    params: GraphQLHttpParams,
    request: DjangoRequestProtocol,
) -> AsyncIterator[NextEventDC | CompletedEventDC]:
    """Execute a GraphQL operation received through server-sent events in distinct connections mode."""
    stream = await execute_graphql_with_subscription(params, request)

    if not isinstance(stream, AsyncIterator):
        yield NextEventDC(data=stream.formatted)
        yield CompletedEventDC()
        return

    try:
        async for data in stream:
            yield NextEventDC(data=data.formatted)

    except GraphQLError as error:
        result = get_error_execution_result(error)
        yield NextEventDC(data=result.formatted)

    except GraphQLErrorGroup as error:
        result = get_error_execution_result(error)
        yield NextEventDC(data=result.formatted)

    except Exception as error:  # noqa: BLE001
        result = get_error_execution_result(GraphQLUnexpectedError(message=str(error)))
        yield NextEventDC(data=result.formatted)

    yield CompletedEventDC()


async def result_to_sse_dc(result: ExecutionResult) -> AsyncIterator[NextEventDC | CompletedEventDC]:  # noqa: RUF029
    """Get iterator for a single result received through server-sent events in distinct connections mode."""
    yield NextEventDC(data=result.formatted)
    yield CompletedEventDC()


async def with_keep_alive_dc(
    event_stream: AsyncIterator[NextEventDC | CompletedEventDC],
) -> AsyncIterator[NextEventDC | CompletedEventDC | KeepAliveSignalDC]:
    """Wrap an event stream to periodically emit SSE keep-alive comments."""
    interval = undine_settings.SSE_KEEP_ALIVE_INTERVAL
    if not interval:
        async for event in event_stream:
            yield event
        return

    yield KeepAliveSignalDC()

    events = aiter(event_stream)
    next_event = asyncio.ensure_future(anext(events))
    try:
        while True:
            done, _ = await asyncio.wait({next_event}, timeout=interval)
            if not done:
                yield KeepAliveSignalDC()
                continue

            try:
                yield next_event.result()
            except StopAsyncIteration:
                return

            next_event = asyncio.ensure_future(anext(events))

    finally:
        if not next_event.done():
            next_event.cancel()
