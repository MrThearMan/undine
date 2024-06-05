from __future__ import annotations

from django.http import HttpResponse

from undine.settings import undine_settings


class HttpMethodNotAllowedResponse(HttpResponse):
    def __init__(self) -> None:
        msg = "Method not allowed"
        response = super().__init__(content=msg, content_type="text/plain; charset=utf-8")
        response["Allow"] = "GET, POST"


class HttpUnsupportedContentTypeResponse(HttpResponse):
    def __init__(self) -> None:
        msg = "Server does not support any of the requested content types."
        response = super().__init__(content=msg, status=406, content_type="text/plain; charset=utf-8")
        response["Accept"] = "application/graphql-response+json, application/json" + (
            ", text/html" if undine_settings.GRAPHIQL_ENABLED else ""
        )
