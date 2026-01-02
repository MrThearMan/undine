from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from graphql import GraphQLError

from undine.dataclasses import CompletedEventDC, NextEventDC
from undine.exceptions import GraphQLErrorGroup, GraphQLUnexpectedError
from undine.execution import execute_graphql_with_subscription
from undine.utils.graphql.utils import get_error_execution_result

if TYPE_CHECKING:
    from graphql import ExecutionResult

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol


__all__ = [
    "execute_graphql_sse_dc",
    "result_to_sse_dc",
]


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
