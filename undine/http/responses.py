from __future__ import annotations

import json
from http import HTTPStatus
from typing import TYPE_CHECKING

from django.http import HttpResponse
from django.http.response import ResponseHeaders

if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.http.request import MediaType
    from graphql import ExecutionResult

    from undine.typing import DjangoResponseProtocol, RequestMethod


__all__ = [
    "HttpEventSourcingNotAllowedResponse",
    "HttpMethodNotAllowedResponse",
    "HttpUnsupportedContentTypeResponse",
    "graphql_result_response",
]


class HttpMethodNotAllowedResponse(HttpResponse):
    def __init__(self, allowed_methods: Iterable[RequestMethod]) -> None:
        msg = "Method not allowed"
        super().__init__(content=msg, status=HTTPStatus.METHOD_NOT_ALLOWED, content_type="text/plain; charset=utf-8")
        self["Allow"] = ", ".join(allowed_methods)


class HttpUnsupportedContentTypeResponse(HttpResponse):
    def __init__(self, supported_types: Iterable[MediaType | str]) -> None:
        msg = "Server does not support any of the requested content types."
        super().__init__(content=msg, status=HTTPStatus.NOT_ACCEPTABLE, content_type="text/plain; charset=utf-8")
        self["Accept"] = ", ".join(str(supported_type) for supported_type in supported_types)


class HttpEventSourcingNotAllowedResponse(HttpResponse):
    def __init__(self) -> None:
        msg = "Cannot use Server-Sent Events with HTTP protocol lower than 2.0."
        super().__init__(content=msg, status=HTTPStatus.UPGRADE_REQUIRED, content_type="text/plain; charset=utf-8")
        self["Upgrade"] = "HTTP/2.0"
        self["Connection"] = "Upgrade"


def graphql_result_response(
    result: ExecutionResult,
    *,
    status: int = HTTPStatus.OK,
    content_type: MediaType | None = None,
    headers: ResponseHeaders | None = None,
) -> DjangoResponseProtocol:
    """Serialize the given execution result to an HTTP response."""
    content = json.dumps(result.formatted, separators=(",", ":"))
    headers = headers or ResponseHeaders({})
    headers["Content-Type"] = str(content_type) if content_type is not None else "application/json"
    return HttpResponse(content=content, status=status, headers=headers)
