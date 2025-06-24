from __future__ import annotations

from typing import TYPE_CHECKING

from graphql import ExecutionResult, GraphQLError

from undine.execution import execute_graphql_async, execute_graphql_sync
from undine.http.utils import graphql_result_response, require_graphql_request
from undine.parsers import GraphQLRequestParamsParser

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
        params = GraphQLRequestParamsParser.run(request)  # type: ignore[arg-type]
        result = execute_graphql_sync(params, request)
    except GraphQLError as error:
        result = ExecutionResult(errors=[error])

    return graphql_result_response(result, content_type=request.response_content_type)


@require_graphql_request
async def graphql_view_async(request: DjangoRequestProtocol) -> DjangoResponseProtocol:
    """A async view for GraphQL requests."""
    try:
        params = GraphQLRequestParamsParser.run(request)  # type: ignore[arg-type]
        result = await execute_graphql_async(params, request)
    except GraphQLError as error:
        result = ExecutionResult(errors=[error])

    return graphql_result_response(result, content_type=request.response_content_type)
