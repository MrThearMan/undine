from typing import Callable

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse

from example_project.project.query_logging import capture_database_queries


def sql_log_middleware(get_response: Callable[[WSGIRequest], HttpResponse]) -> Callable[[WSGIRequest], HttpResponse]:
    def middleware(request: WSGIRequest) -> HttpResponse:
        with capture_database_queries(log=True):
            return get_response(request)

    return middleware
