from __future__ import annotations

import json
from functools import wraps
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, ParamSpec, Protocol

from django.http import HttpResponse, JsonResponse
from django.http.request import MediaType

from undine.exceptions import (
    GraphQLMissingContentTypeError,
    GraphQLRequestDecodingError,
    GraphQLUnsupportedContentTypeError,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.http.request import HttpRequest
    from graphql import GraphQLError

    from undine.typing import HttpMethod

__all__ = [
    "HttpMethodNotAllowedResponse",
    "HttpUnsupportedContentTypeResponse",
    "decode_body",
    "get_preferred_response_content_type",
    "load_json_dict",
    "parse_json_body",
    "require_json",
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
    :raises GraphQLDecodeError: If the body cannot be decoded.
    :return: The decoded body.
    """
    try:
        return body.decode(encoding=charset)
    except Exception as error:
        msg = f"Could not decode body with encoding '{charset}'."
        raise GraphQLRequestDecodingError(msg) from error


def load_json_dict(string: str, *, decode_error_msg: str, type_error_msg: str) -> dict[str, Any]:
    """
    Load JSON dict.

    :param string: The string to load.
    :param decode_error_msg: The error message to use if decoding fails.
    :param type_error_msg: The error message to use if the string is not a JSON object.
    :raises GraphQLDecodeError: If decoding fails or the string is not a JSON object.
    :return: The loaded JSON dict.
    """
    try:
        data = json.loads(string)
    except Exception as error:
        raise GraphQLRequestDecodingError(decode_error_msg) from error

    if not isinstance(data, dict):
        raise GraphQLRequestDecodingError(type_error_msg)
    return data


P = ParamSpec("P")


class FunctionView(Protocol[P]):
    def __call__(self, request: HttpRequest, *args: P.args, **kwargs: P.kwargs) -> HttpResponse: ...


def require_json(func: FunctionView[P]) -> FunctionView[P]:
    """Decorated view requires 'application/json' content type for both input and output data."""
    content_type = "application/json"

    @wraps(func)
    def wrapper(request: HttpRequest, *args: P.args, **kwargs: P.kwargs) -> HttpResponse:
        media_type = get_preferred_response_content_type(accepted=request.accepted_types, supported=[content_type])
        if media_type is None:
            return HttpUnsupportedContentTypeResponse(supported_types=[content_type])

        if request.content_type is None:  # pragma: no cover
            error: GraphQLError = GraphQLMissingContentTypeError()
            return JsonResponse(data={"errors": [error.formatted]}, status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

        if not MediaType(request.content_type).match(content_type):
            error = GraphQLUnsupportedContentTypeError(content_type=request.content_type)
            return JsonResponse(data={"errors": [error.formatted]}, status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

        return func(request, *args, **kwargs)

    return wrapper
