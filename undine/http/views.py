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
    require_graphql_request,
)
from undine.parsers import GraphQLRequestParamsParser
from undine.settings import undine_settings
from undine.utils.graphql.server_sent_events import execute_graphql_sse_dc, result_to_sse_dc
from undine.utils.graphql.utils import get_error_execution_result

if TYPE_CHECKING:
    from undine.typing import DjangoRequestProtocol, DjangoResponseProtocol

__all__ = [
    "graphql_view_async",
    "graphql_view_sync",
]


@require_graphql_request
def graphql_view_sync(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    """A sync view for GraphQL requests."""
    try:
        params = GraphQLRequestParamsParser.run(request)
    except (GraphQLError, GraphQLErrorGroup) as error:
        result = get_error_execution_result(error)
    else:
        result = execute_graphql_http_sync(params, request)

    return graphql_result_response(result, content_type=request.response_content_type)


@require_graphql_request
async def graphql_view_async(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    """An async view for GraphQL requests."""
    if request.response_content_type == "text/event-stream":
        if get_http_version(request) < (2, 0) and not undine_settings.ALLOW_SSE_WITH_HTTP_1_1:
            return HttpEventSourcingNotAllowedResponse()

        try:
            params = GraphQLRequestParamsParser.run(request)
        except (GraphQLError, GraphQLErrorGroup) as error:
            result = get_error_execution_result(error)
            event_stream = result_to_sse_dc(result)
        else:
            event_stream = execute_graphql_sse_dc(params=params, request=request)

        return StreamingHttpResponse(event_stream, content_type=request.response_content_type)

    try:
        params = GraphQLRequestParamsParser.run(request)
    except (GraphQLError, GraphQLErrorGroup) as error:
        result = get_error_execution_result(error)
    else:
        result = await execute_graphql_http_async(params, request)

    return graphql_result_response(result, content_type=request.response_content_type)
