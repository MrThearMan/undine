from __future__ import annotations

import traceback
from typing import TYPE_CHECKING, Any, Callable

from undine.testing.query_logging import capture_database_queries
from undine.utils.logging import undine_logger

if TYPE_CHECKING:
    from django.core.handlers.wsgi import WSGIRequest
    from django.http import HttpResponse
    from graphql import GraphQLFieldResolver

    from undine.typing import GQLInfo


def sql_log_middleware(get_response: Callable[[WSGIRequest], HttpResponse]) -> Callable[[WSGIRequest], HttpResponse]:
    def middleware(request: WSGIRequest) -> HttpResponse:
        with capture_database_queries(log=True):
            return get_response(request)

    return middleware


def error_logging_middleware(resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
    try:
        return resolver(root, info, **kwargs)
    except Exception:
        undine_logger.error(traceback.format_exc())
        raise
