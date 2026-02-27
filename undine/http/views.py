from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import StreamingHttpResponse
from graphql import GraphQLError

from undine.exceptions import GraphQLErrorGroup
from undine.execution import execute_graphql_http_async, execute_graphql_http_sync
from undine.http.utils import (
    HttpEventSourcingNotAllowedResponse,
    get_http_version,
    graphql_result_response,
    require_graphql_request_async,
    require_graphql_request_sync,
)
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

    return graphql_result_response(result, content_type=request.response_content_type)


@require_graphql_request_async
async def graphql_view_async(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    """An async view for GraphQL requests."""
    if request.response_content_type == "text/event-stream":
        return await _handle_event_stream(request)

    if request.response_content_type == "multipart/mixed":
        return await _handle_multipart_mixed(request)

    try:
        params = GraphQLRequestParamsParser.run(request)
    except (GraphQLError, GraphQLErrorGroup) as error:
        result = get_error_execution_result(error)
    else:
        result = await execute_graphql_http_async(params, request)

    return graphql_result_response(result, content_type=request.response_content_type)


async def _handle_event_stream(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    # Single connection mode is handled by Channels integration.
    if get_http_version(request) < (2, 0) and not undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1:
        return HttpEventSourcingNotAllowedResponse()

    try:
        params = GraphQLRequestParamsParser.run(request)
    except (GraphQLError, GraphQLErrorGroup) as error:
        result = get_error_execution_result(error)
        event_stream = result_to_sse_dc(result)
    else:
        event_stream = execute_graphql_sse_dc(params=params, request=request)

    stream: AsyncIterable[str] = (event.encode() async for event in with_keep_alive_dc(event_stream))

    content_type = "text/event-stream; charset=utf-8"
    return StreamingHttpResponse(stream, content_type=content_type)


async def _handle_multipart_mixed(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    try:
        params = GraphQLRequestParamsParser.run(request)
    except (GraphQLError, GraphQLErrorGroup) as error:
        result = get_error_execution_result(error)
        event_stream = result_to_multipart_mixed_response(result)
    else:
        event_stream = execute_graphql_multipart_mixed(params, request)

    stream: AsyncIterable[str] = (event.encode() async for event in with_multipart_mixed_heartbeat(event_stream))

    content_type = 'multipart/mixed;boundary=graphql;subscriptionSpec="1.0", application/json'
    return StreamingHttpResponse(stream, content_type=content_type)
