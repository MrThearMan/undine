from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from functools import wraps
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, TypeAlias

from django.http import HttpRequest, HttpResponse
from django.http.request import MediaType

from undine.exceptions import (
    GraphQLMissingContentTypeError,
    GraphQLRequestDecodingError,
    GraphQLUnsupportedContentTypeError,
)
from undine.integrations.graphiql import render_graphiql
from undine.settings import undine_settings
from undine.typing import DjangoRequestProtocol, DjangoResponseProtocol
from undine.utils.graphql.utils import get_error_execution_result

if TYPE_CHECKING:
    from collections.abc import Iterable

    from graphql import ExecutionResult

    from undine.typing import RequestMethod

__all__ = [
    "HttpEventSourcingNotAllowedResponse",
    "HttpMethodNotAllowedResponse",
    "HttpUnsupportedContentTypeResponse",
    "decode_body",
    "get_preferred_response_content_type",
    "graphql_result_response",
    "is_sse_request",
    "is_websocket_request",
    "load_json_dict",
    "parse_json_body",
    "render_graphiql",
    "require_graphql_request_async",
    "require_graphql_request_sync",
    "require_persisted_documents_request",
]


class HttpMethodNotAllowedResponse(HttpResponse):
    def __init__(self, allowed_methods: Iterable[RequestMethod]) -> None:
        msg = "Method not allowed"
        super().__init__(content=msg, status=HTTPStatus.METHOD_NOT_ALLOWED, content_type="text/plain; charset=utf-8")
        self["Allow"] = ", ".join(allowed_methods)


class HttpUnsupportedContentTypeResponse(HttpResponse):
    def __init__(self, supported_types: Iterable[str]) -> None:
        msg = "Server does not support any of the requested content types."
        super().__init__(content=msg, status=HTTPStatus.NOT_ACCEPTABLE, content_type="text/plain; charset=utf-8")
        self["Accept"] = ", ".join(supported_types)


class HttpEventSourcingNotAllowedResponse(HttpResponse):
    def __init__(self) -> None:
        msg = "Cannot use Server-Sent Events with HTTP protocol lower than 2.0."
        super().__init__(content=msg, status=HTTPStatus.UPGRADE_REQUIRED, content_type="text/plain; charset=utf-8")
        self["Upgrade"] = "HTTP/2.0"
        self["Connection"] = "Upgrade"


def get_preferred_response_content_type(accepted: list[MediaType], supported: list[str]) -> str | None:
    """
    Get the first supported media type matching given accepted types.

    :param accepted: The accepted media types.
    :param supported: The supported media types, in order of preference.
    :returns: The first supported media type matching given accepted types.
    """
    for accepted_type in accepted:
        for supported_type in supported:
            if accepted_type.match(supported_type):
                return supported_type
    return None


def parse_json_body(body: bytes, charset: str = "utf-8") -> dict[str, Any]:
    """
    Parse JSON body.

    :param body: The body to parse.
    :param charset: The charset to decode the body with.
    :raises GraphQLDecodeError: If the body cannot be decoded.
    :return: The parsed JSON body.
    """
    decoded = decode_body(body, charset=charset)
    return load_json_dict(
        decoded,
        decode_error_msg="Could not load JSON body.",
        type_error_msg="JSON body should convert to a dictionary.",
    )


def decode_body(body: bytes, charset: str = "utf-8") -> str:
    """
    Decode body.

    :param body: The body to decode.
    :param charset: The charset to decode the body with.
    :raises GraphQLRequestDecodingError: If the body cannot be decoded.
    :return: The decoded body.
    """
    try:
        return body.decode(encoding=charset)
    except Exception as error:
        msg = f"Could not decode body with encoding '{charset}'."
        raise GraphQLRequestDecodingError(msg) from error


def load_json_dict(string: str, *, decode_error_msg: str, type_error_msg: str) -> dict[str, Any]:
    """
    Load JSON dict from string, raising GraphQL errors if decoding fails.

    :param string: The string to load.
    :param decode_error_msg: The error message to use if decoding fails.
    :param type_error_msg: The error message to use if the string is not a JSON object.
    :raises GraphQLRequestDecodingError: If decoding fails or the string is not a JSON object.
    :return: The loaded JSON dict.
    """
    try:
        data = json.loads(string)
    except Exception as error:
        raise GraphQLRequestDecodingError(decode_error_msg) from error

    if not isinstance(data, dict):
        raise GraphQLRequestDecodingError(type_error_msg)
    return data


def is_sse_request(request: DjangoRequestProtocol) -> bool:
    """Check if the given request is a Server-Sent Events request."""
    if get_graphql_event_stream_token(request):
        return True

    if not request.response_content_type:
        return False

    content_type = MediaType(request.response_content_type)
    return content_type.match("text/event-stream")


def is_websocket_request(request: DjangoRequestProtocol) -> bool:
    """Check if the given request is a WebSocket request."""
    return request.method == "WEBSOCKET"


def get_http_version(request: DjangoRequestProtocol) -> tuple[int, ...]:
    """
    Get the HTTP version of the given request.
    Only really reliable for ASGI requests.
    """
    # ASGI requests will have the HTTP version in the ASGI scope
    scope: dict[str, Any] | None = getattr(request, "scope", None)
    if scope is not None:
        protocol = scope["http_version"]

    # WSGI requests will have the server protocol in the META, but this might be
    # different to what the client is sending if behind a proxy.
    else:
        protocol = request.META.get("SERVER_PROTOCOL", "0").removeprefix("HTTP/")

    return tuple(int(part) for part in str(float(protocol)).split("."))


def get_graphql_event_stream_token(request: DjangoRequestProtocol) -> str | None:
    """Get the GraphQL over SSE event stream token from the given request."""
    if undine_settings.SSE_TOKEN_HEADER_NAME in request.headers:
        return request.headers[undine_settings.SSE_TOKEN_HEADER_NAME]
    if undine_settings.SSE_TOKEN_QUERY_PARAM_NAME in request.GET:
        return request.GET[undine_settings.SSE_TOKEN_QUERY_PARAM_NAME]
    return None


def graphql_result_response(
    result: ExecutionResult,
    *,
    status: int = HTTPStatus.OK,
    content_type: str = "application/json",
) -> DjangoResponseProtocol:
    """Serialize the given execution result to an HTTP response."""
    content = json.dumps(result.formatted, separators=(",", ":"))
    return HttpResponse(content=content, status=status, content_type=content_type)  # type: ignore[return-value]


SyncViewIn: TypeAlias = Callable[[DjangoRequestProtocol], DjangoResponseProtocol]
AsyncViewIn: TypeAlias = Callable[[DjangoRequestProtocol], Awaitable[DjangoResponseProtocol]]

SyncViewOut: TypeAlias = Callable[[HttpRequest], HttpResponse]
AsyncViewOut: TypeAlias = Callable[[HttpRequest], Awaitable[HttpResponse]]


def require_graphql_request_sync(func: SyncViewIn) -> SyncViewOut:
    """
    Perform various checks on the request to ensure it's suitable for GraphQL operations in a synchronous server.
    Can also return early to display GraphiQL.
    """
    allowed_methods: list[RequestMethod] = ["GET", "POST"]

    @wraps(func)
    def wrapper(request: DjangoRequestProtocol) -> DjangoResponseProtocol | HttpResponse:
        if request.method not in allowed_methods:
            return HttpMethodNotAllowedResponse(allowed_methods=allowed_methods)

        supported_types: list[str] = [
            "application/graphql-response+json",
            "application/json",
        ]
        if request.method == "GET" and undine_settings.GRAPHIQL_ENABLED:
            supported_types.append("text/html")

        media_type = get_preferred_response_content_type(accepted=request.accepted_types, supported=supported_types)
        if media_type is None:
            return HttpUnsupportedContentTypeResponse(supported_types=supported_types)

        # 'test/html' is reserved for GraphiQL which must use GET
        if media_type == "text/html":
            if request.method != "GET":
                return HttpMethodNotAllowedResponse(allowed_methods=["GET"])
            return render_graphiql(request)  # type: ignore[arg-type]

        request.response_content_type = media_type
        return func(request)  # type: ignore[return-value]

    return wrapper  # type: ignore[return-value]


def require_graphql_request_async(func: AsyncViewIn) -> AsyncViewOut:
    """
    Perform various checks on the request to ensure it's suitable for GraphQL operations in an asynchronous server.
    Can also return early to display GraphiQL.
    """
    allowed_methods: list[RequestMethod] = ["GET", "POST"]

    @wraps(func)
    async def wrapper(request: DjangoRequestProtocol) -> DjangoResponseProtocol | HttpResponse:
        if request.method not in allowed_methods:
            return HttpMethodNotAllowedResponse(allowed_methods=allowed_methods)

        supported_types: list[str] = [
            "application/graphql-response+json",
            "application/json",
            "text/event-stream",
        ]
        if request.method == "GET" and undine_settings.GRAPHIQL_ENABLED:
            supported_types.append("text/html")

        media_type = get_preferred_response_content_type(accepted=request.accepted_types, supported=supported_types)
        if media_type is None:
            return HttpUnsupportedContentTypeResponse(supported_types=supported_types)

        # 'test/html' is reserved for GraphiQL which must use GET
        if media_type == "text/html":
            if request.method != "GET":
                return HttpMethodNotAllowedResponse(allowed_methods=["GET"])
            return render_graphiql(request)  # type: ignore[arg-type]

        request.response_content_type = media_type
        return await func(request)

    return wrapper  # type: ignore[return-value]


def require_persisted_documents_request(func: SyncViewIn) -> SyncViewOut:
    """Perform various checks on the request to ensure that it's suitable for registering persisted documents."""
    content_type: str = "application/json"
    methods: list[RequestMethod] = ["POST"]

    @wraps(func)
    def wrapper(request: DjangoRequestProtocol) -> DjangoResponseProtocol | HttpResponse:
        if request.method not in methods:
            return HttpMethodNotAllowedResponse(allowed_methods=methods)

        media_type = get_preferred_response_content_type(accepted=request.accepted_types, supported=[content_type])
        if media_type is None:
            return HttpUnsupportedContentTypeResponse(supported_types=[content_type])

        request.response_content_type = media_type

        if request.content_type is None:  # pragma: no cover
            result = get_error_execution_result(GraphQLMissingContentTypeError())
            return graphql_result_response(result, status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE, content_type=media_type)

        if not MediaType(request.content_type).match(content_type):
            result = get_error_execution_result(GraphQLUnsupportedContentTypeError(content_type=request.content_type))
            return graphql_result_response(result, status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE, content_type=media_type)

        return func(request)

    return wrapper  # type: ignore[return-value]
