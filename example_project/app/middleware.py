from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from undine.testing.query_logging import capture_database_queries

if TYPE_CHECKING:
    from django.core.handlers.wsgi import WSGIRequest
    from django.http import HttpResponse


def sql_log_middleware(get_response: Callable[[WSGIRequest], HttpResponse]) -> Callable[[WSGIRequest], HttpResponse]:
    def middleware(request: WSGIRequest) -> HttpResponse:
        with capture_database_queries(log=True):
            return get_response(request)

    return middleware
