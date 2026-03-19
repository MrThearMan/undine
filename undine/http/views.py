from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import StreamingHttpResponse
from graphql import GraphQLError

from undine.exceptions import GraphQLErrorGroup
from undine.execution import execute_graphql_http_async, execute_graphql_http_sync
from undine.http.content_negotiation import (
    media_type_match,
    require_graphql_request_async,
    require_graphql_request_sync,
)
from undine.http.responses import HttpEventSourcingNotAllowedResponse, graphql_result_response
from undine.http.utils import get_http_version
from undine.parsers import GraphQLRequestParamsParser
from undine.settings import undine_settings
from undine.utils.graphql.multipart_mixed import (
    execute_graphql_multipart_mixed,
    result_to_multipart_mixed_response,
    with_multipart_mixed_heartbeat,
)
from undine.utils.graphql.server_sent_events import execute_graphql_sse_dc, result_to_sse_dc, with_keep_alive_dc
from undine.utils.graphql.utils import get_error_execution_result

if TYPE_CHECKING:
    from collections.abc import AsyncIterable

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

    return graphql_result_response(
        result,
        content_type=request.response_content_type,
        headers=request.response_headers,
    )


@require_graphql_request_async
async def graphql_view_async(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    """An async view for GraphQL requests."""
    if media_type_match(request.response_content_type, "text/event-stream"):
        return await _handle_event_stream(request)

    if media_type_match(request.response_content_type, "multipart/mixed; boundary=graphql; subscriptionSpec=1.0"):
        return await _handle_multipart_mixed(request)

    if media_type_match(request.response_content_type, "multipart/mixed; boundary=graphql"):
        return await _handle_incremental(request)

    try:
        params = await GraphQLRequestParamsParser.run_async(request)
    except (GraphQLError, GraphQLErrorGroup) as error:
        result = get_error_execution_result(error)
    else:
        result = await execute_graphql_http_async(params, request)

    return graphql_result_response(
        result,
        content_type=request.response_content_type,
        headers=request.response_headers,
    )


async def _handle_event_stream(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    # Single connection mode is handled by Channels integration.
    if get_http_version(request) < (2, 0) and not undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1:
        return HttpEventSourcingNotAllowedResponse()

    try:
        params = await GraphQLRequestParamsParser.run_async(request)
    except (GraphQLError, GraphQLErrorGroup) as error:
        result = get_error_execution_result(error)
        event_stream = result_to_sse_dc(result)
    else:
        event_stream = execute_graphql_sse_dc(params=params, request=request)

    stream: AsyncIterable[str] = (event.encode() async for event in with_keep_alive_dc(event_stream))

    headers = request.response_headers.copy()
    headers["Connection"] = "keep-alive"
    headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    headers["Content-Type"] = str(request.response_content_type)
    headers.pop("Content-Length", None)

    return StreamingHttpResponse(stream, headers=headers)


async def _handle_multipart_mixed(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    try:
        params = await GraphQLRequestParamsParser.run_async(request)
    except (GraphQLError, GraphQLErrorGroup) as error:
        result = get_error_execution_result(error)
        event_stream = result_to_multipart_mixed_response(result)
    else:
        event_stream = execute_graphql_multipart_mixed(params, request)

    stream: AsyncIterable[str] = (event.encode() async for event in with_multipart_mixed_heartbeat(event_stream))

    headers = request.response_headers.copy()
    headers["Connection"] = "keep-alive"
    headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    headers["Content-Type"] = str(request.response_content_type)
    headers.pop("Content-Length", None)

    return StreamingHttpResponse(stream, headers=headers)


async def _handle_incremental(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    from undine.utils.graphql.incremental import (  # noqa: PLC0415
        execute_graphql_incremental,
        result_to_incremental_response,
        with_incremental_stream_heartbeat,
    )

    try:
        params = await GraphQLRequestParamsParser.run_async(request)
    except (GraphQLError, GraphQLErrorGroup) as error:
        result = get_error_execution_result(error)
        event_stream = result_to_incremental_response(result)
    else:
        event_stream = execute_graphql_incremental(params, request)

    stream: AsyncIterable[str] = (event.encode() async for event in with_incremental_stream_heartbeat(event_stream))

    headers = request.response_headers.copy()
    headers["Connection"] = "keep-alive"
    headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    headers["Content-Type"] = str(request.response_content_type)
    headers.pop("Content-Length", None)

    return StreamingHttpResponse(stream, headers=headers)
