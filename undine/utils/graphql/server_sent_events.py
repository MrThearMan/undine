from __future__ import annotations

import dataclasses
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from django.core.cache import cache
from graphql import GraphQLError

from undine.dataclasses import (
    CompletedEventDataSC,
    CompletedEventDC,
    CompletedEventSC,
    NextEventDataSC,
    NextEventDC,
    NextEventSC,
)
from undine.exceptions import GraphQLErrorGroup, GraphQLUnexpectedError
from undine.execution import execute_graphql_with_subscription
from undine.settings import undine_settings
from undine.utils.graphql.utils import get_error_execution_result

if TYPE_CHECKING:
    from graphql import ExecutionResult

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol, SSEProtocol

__all__ = [
    "execute_graphql_sse_dc",
    "execute_graphql_sse_sc",
    "result_to_sse_dc",
    "result_to_sse_sc",
]


# Distinct connections mode


async def execute_graphql_sse_dc(params: GraphQLHttpParams, request: DjangoRequestProtocol) -> AsyncIterator[str]:
    """Execute a GraphQL operation received through server-sent events in distinct connections mode."""
    stream = await execute_graphql_with_subscription(params, request)

    if not isinstance(stream, AsyncIterator):
        async for event in result_to_sse_dc(stream):
            yield event
        return

    try:
        async for data in stream:
            yield NextEventDC(event="next", data=data.formatted).encode()

    except GraphQLError as error:
        result = get_error_execution_result(error)
        yield NextEventDC(event="next", data=result.formatted).encode()

    except GraphQLErrorGroup as error:
        result = get_error_execution_result(error)
        yield NextEventDC(event="next", data=result.formatted).encode()

    except Exception as error:  # noqa: BLE001
        result = get_error_execution_result(GraphQLUnexpectedError(message=str(error)))
        yield NextEventDC(event="next", data=result.formatted).encode()

    yield CompletedEventDC(event="complete", data=None).encode()


async def result_to_sse_dc(result: ExecutionResult) -> AsyncIterator[str]:  # noqa: RUF029
    """Get iterator for a single result received through server-sent events in distinct connections mode."""
    yield NextEventDC(event="next", data=result.formatted).encode()
    yield CompletedEventDC(event="complete", data=None).encode()


# Single connections mode


@dataclasses.dataclass(kw_only=True, slots=True)
class GraphQLOverSSEHandler:
    """Handler for the GraphQL over SSE Protocol."""

    sse: SSEProtocol


async def execute_graphql_sse_sc(params: GraphQLHttpParams, request: DjangoRequestProtocol) -> AsyncIterator[str]:
    """Execute a GraphQL operation received through server-sent events in single connections mode."""
    # TODO: Implement


async def result_to_sse_sc(operation_id: str, result: ExecutionResult) -> AsyncIterator[str]:  # noqa: RUF029
    """Get iterator for a single result received through server-sent events in distinct connections mode."""
    yield NextEventSC(event="next", data=NextEventDataSC(id=operation_id, data=result.formatted)).encode()
    yield CompletedEventSC(event="complete", data=CompletedEventDataSC(id=operation_id)).encode()


async def stream_exists(stream_token: str) -> bool:
    """Check if a stream exists in the cache."""
    key = f"{undine_settings.SSE_CACHE_PREFIX}|{stream_token}"
    return (await cache.aget(key, default=None)) is not None


async def create_stream(stream_token: str) -> None:
    """Create a stream in the cache."""
    key = f"{undine_settings.SSE_CACHE_PREFIX}|{stream_token}"
    await cache.aadd(key=key, value=0)


async def activate_stream(stream_token: str) -> int:
    """
    Activate a stream in the cache.

    If this returns `1`, then this attempt should be considered successful.
    Otherwise, the there was a race condition and another process has already activated the stream.
    """
    key = f"{undine_settings.SSE_CACHE_PREFIX}|{stream_token}"
    return await cache.aincr(key=key)


async def delete_stream(stream_token: str) -> None:
    """Delete a stream from the cache."""
    key = f"{undine_settings.SSE_CACHE_PREFIX}|{stream_token}"
    await cache.adelete(key=key)
