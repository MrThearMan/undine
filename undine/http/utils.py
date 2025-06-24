from __future__ import annotations

import json
from asyncio import iscoroutinefunction
from collections.abc import Awaitable, Callable
from functools import wraps
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, TypeAlias, overload

from django.http import HttpRequest, HttpResponse
from django.http.request import MediaType
from django.shortcuts import render
from graphql import ExecutionResult

from undine.exceptions import (
    GraphQLMissingContentTypeError,
    GraphQLRequestDecodingError,
    GraphQLUnsupportedContentTypeError,
)
from undine.settings import undine_settings
from undine.typing import DjangoRequestProtocol, DjangoResponseProtocol

if TYPE_CHECKING:
    from collections.abc import Iterable

    from graphql import GraphQLError

    from undine.exceptions import GraphQLErrorGroup
    from undine.typing import HttpMethod

__all__ = [
    "HttpMethodNotAllowedResponse",
    "HttpUnsupportedContentTypeResponse",
    "decode_body",
    "get_preferred_response_content_type",
    "graphql_error_group_response",
    "graphql_error_response",
    "graphql_result_response",
    "load_json_dict",
    "parse_json_body",
    "require_graphql_request",
    "require_persisted_documents_request",
]


class HttpMethodNotAllowedResponse(HttpResponse):
    def __init__(self, allowed_methods: Iterable[HttpMethod]) -> None:
        msg = "Method not allowed"
        super().__init__(content=msg, status=HTTPStatus.METHOD_NOT_ALLOWED, content_type="text/plain; charset=utf-8")
        self["Allow"] = ", ".join(allowed_methods)


class HttpUnsupportedContentTypeResponse(HttpResponse):
    def __init__(self, supported_types: Iterable[str]) -> None:
        msg = "Server does not support any of the requested content types."
        super().__init__(content=msg, status=HTTPStatus.NOT_ACCEPTABLE, content_type="text/plain; charset=utf-8")
        self["Accept"] = ", ".join(supported_types)


def get_preferred_response_content_type(accepted: list[MediaType], supported: list[str]) -> str | None:
    """Get the first supported media type matching given accepted types."""
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


def graphql_result_response(
    result: ExecutionResult,
    *,
    status: int = HTTPStatus.OK,
    content_type: str = "application/json",
) -> DjangoResponseProtocol:
    """Serialize the given execution result to an HTTP response."""
    content = json.dumps(result.formatted, separators=(",", ":"))
    return HttpResponse(content=content, status=status, content_type=content_type)  # type: ignore[return-value]


def graphql_error_response(
    error: GraphQLError,
    *,
    status: int = HTTPStatus.OK,
    content_type: str = "application/json",
) -> DjangoResponseProtocol:
    """Serialize the given GraphQL error to an HTTP response."""
    result = ExecutionResult(errors=[error])
    return graphql_result_response(result, status=status, content_type=content_type)


def graphql_error_group_response(
    error: GraphQLErrorGroup,
    *,
    status: int = HTTPStatus.OK,
    content_type: str = "application/json",
) -> DjangoResponseProtocol:
    """Serialize the given GraphQL error group to an HTTP response."""
    result = ExecutionResult(errors=list(error.flatten()))
    return graphql_result_response(result, status=status, content_type=content_type)


SyncViewIn: TypeAlias = Callable[[DjangoRequestProtocol], DjangoResponseProtocol]
AsyncViewIn: TypeAlias = Callable[[DjangoRequestProtocol], Awaitable[DjangoResponseProtocol]]

SyncViewOut: TypeAlias = Callable[[HttpRequest], HttpResponse]
AsyncViewOut: TypeAlias = Callable[[HttpRequest], Awaitable[HttpResponse]]


@overload
def require_graphql_request(func: SyncViewIn) -> SyncViewOut: ...


@overload
def require_graphql_request(func: AsyncViewIn) -> AsyncViewOut: ...


def require_graphql_request(func: SyncViewIn | AsyncViewIn) -> SyncViewOut | AsyncViewOut:
    """
    Perform various checks on the request to ensure it's suitable for GraphQL operations.
    Can also return early to display GraphiQL.
    """
    methods: list[HttpMethod] = ["GET", "POST"]

    def get_supported_types() -> list[str]:
        supported_types = ["application/graphql-response+json", "application/json"]
        if undine_settings.GRAPHIQL_ENABLED:
            supported_types.append("text/html")
        return supported_types

    if iscoroutinefunction(func):

        @wraps(func)
        async def wrapper(request: DjangoRequestProtocol) -> DjangoResponseProtocol | HttpResponse:
            if request.method not in methods:
                return HttpMethodNotAllowedResponse(allowed_methods=methods)

            supported_types = get_supported_types()
            media_type = get_preferred_response_content_type(accepted=request.accepted_types, supported=supported_types)
            if media_type is None:
                return HttpUnsupportedContentTypeResponse(supported_types=supported_types)

            if media_type == "text/html":
                return render(request, "undine/graphiql.html")  # type: ignore[arg-type]

            request.response_content_type = media_type
            return await func(request)

    else:

        @wraps(func)
        def wrapper(request: DjangoRequestProtocol) -> DjangoResponseProtocol | HttpResponse:
            if request.method not in methods:
                return HttpMethodNotAllowedResponse(allowed_methods=methods)

            supported_types = get_supported_types()
            media_type = get_preferred_response_content_type(accepted=request.accepted_types, supported=supported_types)
            if media_type is None:
                return HttpUnsupportedContentTypeResponse(supported_types=supported_types)

            if media_type == "text/html":
                return render(request, "undine/graphiql.html")  # type: ignore[arg-type]

            request.response_content_type = media_type
            return func(request)  # type: ignore[return-value]

    return wrapper  # type: ignore[return-value]


def require_persisted_documents_request(func: SyncViewIn) -> SyncViewOut:
    """Perform various checks on the request to ensure that it's suitable for registering persisted documents."""
    content_type: str = "application/json"
    methods: list[HttpMethod] = ["POST"]

    @wraps(func)
    def wrapper(request: DjangoRequestProtocol) -> DjangoResponseProtocol | HttpResponse:
        if request.method not in methods:
            return HttpMethodNotAllowedResponse(allowed_methods=methods)

        media_type = get_preferred_response_content_type(accepted=request.accepted_types, supported=[content_type])
        if media_type is None:
            return HttpUnsupportedContentTypeResponse(supported_types=[content_type])

        request.response_content_type = media_type

        if request.content_type is None:  # pragma: no cover
            return graphql_error_response(
                error=GraphQLMissingContentTypeError(),
                status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                content_type=media_type,
            )

        if not MediaType(request.content_type).match(content_type):
            return graphql_error_response(
                error=GraphQLUnsupportedContentTypeError(content_type=request.content_type),
                status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                content_type=media_type,
            )

        return func(request)

    return wrapper  # type: ignore[return-value]
