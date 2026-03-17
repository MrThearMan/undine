from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from undine.exceptions import GraphQLRequestDecodingError
from undine.integrations.graphiql import render_graphiql
from undine.settings import undine_settings

if TYPE_CHECKING:
    from undine.typing import DjangoRequestProtocol

__all__ = [
    "decode_body",
    "get_graphql_event_stream_token",
    "get_http_version",
    "load_json_dict",
    "parse_json_body",
    "render_graphiql",
]


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
        return request.GET[undine_settings.SSE_TOKEN_QUERY_PARAM_NAME]  # type: ignore[return-value]
    return None
