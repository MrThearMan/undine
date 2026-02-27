from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from graphql import GraphQLError

from undine.dataclasses import MultipartMixedHttpComplete, MultipartMixedHttpHeartbeat, MultipartMixedHttpResponse
from undine.exceptions import GraphQLErrorGroup, GraphQLUnexpectedError
from undine.execution import execute_graphql_with_subscription
from undine.settings import undine_settings
from undine.utils.graphql.utils import get_error_execution_result

if TYPE_CHECKING:
    from graphql import ExecutionResult

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol

__all__ = [
    "execute_graphql_multipart_mixed",
    "result_to_multipart_mixed_response",
    "with_multipart_mixed_heartbeat",
]


async def execute_graphql_multipart_mixed(
    params: GraphQLHttpParams,
    request: DjangoRequestProtocol,
) -> AsyncIterator[MultipartMixedHttpResponse | MultipartMixedHttpComplete]:
    """Execute a GraphQL operation received through a multipart/mixed HTTP request."""
    stream = await execute_graphql_with_subscription(params, request)

    if not isinstance(stream, AsyncIterator):
        yield MultipartMixedHttpResponse(payload=stream)
        yield MultipartMixedHttpComplete()
        return

    try:
        async for data in stream:
            yield MultipartMixedHttpResponse(payload=data)

    except GraphQLError as error:
        yield MultipartMixedHttpResponse(payload=get_error_execution_result(error))

    except GraphQLErrorGroup as error:
        yield MultipartMixedHttpResponse(payload=get_error_execution_result(error))

    except Exception as error:  # noqa: BLE001
        yield MultipartMixedHttpResponse(payload=get_error_execution_result(GraphQLUnexpectedError(message=str(error))))

    yield MultipartMixedHttpComplete()


async def result_to_multipart_mixed_response(  # noqa: RUF029
    result: ExecutionResult,
) -> AsyncIterator[MultipartMixedHttpResponse | MultipartMixedHttpComplete]:
    """Get iterator for a single result received through a multipart/mixed HTTP request."""
    yield MultipartMixedHttpResponse(payload=result)
    yield MultipartMixedHttpComplete()


async def with_multipart_mixed_heartbeat(
    event_stream: AsyncIterator[MultipartMixedHttpResponse | MultipartMixedHttpComplete],
) -> AsyncIterator[MultipartMixedHttpResponse | MultipartMixedHttpComplete | MultipartMixedHttpHeartbeat]:
    """Wrap an event stream to periodically emit multipart/mixed HTTP heartbeats."""
    interval = undine_settings.MULTIPART_MIXED_HEARTBEAT_INTERVAL
    if not interval:
        async for event in event_stream:
            yield event
        return

    yield MultipartMixedHttpHeartbeat()

    events = aiter(event_stream)
    next_event = asyncio.ensure_future(anext(events))
    try:
        while True:
            done, _ = await asyncio.wait({next_event}, timeout=interval)
            if not done:
                yield MultipartMixedHttpHeartbeat()
                continue

            try:
                yield next_event.result()
            except StopAsyncIteration:
                return

            next_event = asyncio.ensure_future(anext(events))

    finally:
        if not next_event.done():
            next_event.cancel()
