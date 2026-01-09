from __future__ import annotations

import asyncio
from http import HTTPStatus
from typing import TYPE_CHECKING

from django.http import HttpResponse, StreamingHttpResponse
from graphql import GraphQLError

from undine.exceptions import (
    GraphQLErrorGroup,
    GraphQLSSEOperationIdMissingError,
    GraphQLSSEStreamAlreadyOpenError,
    GraphQLSSEStreamNotFoundError,
)
from undine.execution import execute_graphql_http_async, execute_graphql_http_sync
from undine.http.utils import (
    get_graphql_event_stream_token,
    get_http_version,
    graphql_result_response,
    require_graphql_request_async,
    require_graphql_request_sync,
)
from undine.parsers import GraphQLRequestParamsParser
from undine.settings import undine_settings
from undine.utils.graphql.server_sent_events import execute_graphql_sse_dc, result_to_sse_dc, stream_exists
from undine.utils.graphql.utils import get_error_execution_result

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from undine.typing import DjangoRequestProtocol, DjangoResponseProtocol

__all__ = [
    "graphql_view_async",
    "graphql_view_sync",
]


@require_graphql_request_sync
def graphql_view_sync(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    """A sync view for GraphQL requests."""
    try:
        params = GraphQLRequestParamsParser.run(request)
    except (GraphQLError, GraphQLErrorGroup) as error:
        result = get_error_execution_result(error)
    else:
        result = execute_graphql_http_sync(params, request)

    return graphql_result_response(result, content_type=request.response_content_type)


@require_graphql_request_async
async def graphql_view_async(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    """An async view for GraphQL requests."""
    if request.method == "PUT":
        return await handle_event_stream_reservation(request)

    if request.method == "DELETE":
        return await handle_event_stream_cancellation(request)

    # TODO: GET or POST from here on
    #  If method is GET, content type is text/event-stream, and http version is below 2.0,
    #  a token must be provided for single connection mode. Otherwise, return

    if request.response_content_type == "text/event-stream":
        if get_http_version(request) >= (2, 0) or undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1:
            return handle_event_stream_dc(request)
        return handle_event_stream_sc(request)

    try:
        params = GraphQLRequestParamsParser.run(request)
    except (GraphQLError, GraphQLErrorGroup) as error:
        result = get_error_execution_result(error)
    else:
        result = await execute_graphql_http_async(params, request)

    return graphql_result_response(result, content_type=request.response_content_type)


def handle_event_stream_dc(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    try:
        params = GraphQLRequestParamsParser.run(request)
    except (GraphQLError, GraphQLErrorGroup) as error:
        result = get_error_execution_result(error)
        event_stream = result_to_sse_dc(result)
    else:
        event_stream = execute_graphql_sse_dc(params=params, request=request)

    return StreamingHttpResponse(event_stream, content_type=request.response_content_type)


def handle_event_stream_sc(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    # TODO:
    #  Check if stream exists for the given token. If it doesn't, return a 404 (Not Found) response.
    #  If it does, return a 200 (OK) response with the stream.

    queue = asyncio.Queue()

    # TODO: Channel layer for the queue

    async def gen() -> AsyncGenerator[str, None]:
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=15)
                yield message
            except TimeoutError:
                yield "{}\n\n"  # TODO: Keep alive message

    return StreamingHttpResponse(gen(), content_type=request.response_content_type)


async def handle_event_stream_reservation(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    # TODO: Generate stream key from user (must be deterministic).
    stream_token = "<stream-key>"  # noqa: S105

    if await stream_exists(stream_token):
        error = GraphQLSSEStreamAlreadyOpenError()
        result = get_error_execution_result(error)
        return graphql_result_response(result, status=HTTPStatus.CONFLICT)

    # TODO:
    #  Check if stream exists for the given token.
    #  If it does, return a 409 (Conflict) response.
    #  If it doesn't, create set some flag in cache to indicate that the stream exists
    #  and return a 201 (Created) response with the flag. This stream can then be established
    #  with a GET request using the token.
    return HttpResponse(content=stream_token, content_type="text/plain", status=HTTPStatus.CREATED)


async def handle_event_stream_cancellation(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    stream_token = get_graphql_event_stream_token(request)

    if not await stream_exists(stream_token):
        error = GraphQLSSEStreamNotFoundError()
        result = get_error_execution_result(error)
        return graphql_result_response(result, status=HTTPStatus.NOT_FOUND)

    operation_id = request.GET.get("operationId")
    if not operation_id:
        error = GraphQLSSEOperationIdMissingError()
        result = get_error_execution_result(error)
        return graphql_result_response(result, status=HTTPStatus.BAD_REQUEST)

    # Do nothing in case this `operationId` doesn't exist so that the delete operation is idempotent.
    # TODO: Channel layer for the delete operation

    return HttpResponse(status=HTTPStatus.OK)
