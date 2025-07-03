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
    from undine.typing import RequestMethod

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
    "render_graphiql",
    "require_graphql_request",
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
    methods: list[RequestMethod] = ["GET", "POST"]

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
                return render_graphiql(request)  # type: ignore[arg-type]

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
                return render_graphiql(request)  # type: ignore[arg-type]

            request.response_content_type = media_type
            return func(request)  # type: ignore[return-value]

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


def render_graphiql(request: HttpRequest) -> HttpResponse:
    """Render GraphiQL."""
    return render(request, "undine/graphiql.html", context=get_graphiql_context())


def get_graphiql_context() -> dict[str, Any]:
    """Get the GraphiQL context."""
    return {
        "http_path": undine_settings.GRAPHQL_PATH,
        "ws_path": undine_settings.WEBSOCKET_PATH,
        "importmap": get_importmap(),
        # Note that changing the versions here will break integrity checks! Regenerate: https://www.srihash.org/
        "graphiql_css": "https://esm.sh/graphiql@5.0.3/dist/style.css",
        "explorer_css": "https://esm.sh/@graphiql/plugin-explorer@5.0.0/dist/style.css",
        "graphiql_css_integrity": "sha384-lixdMC836B3JdnFulLFPKjIN0gr85IffJ5qBAoYmKxoeNXlkn+JgibHqHBD6N9ef",
        "explorer_css_integrity": "sha384-vTFGj0krVqwFXLB7kq/VHR0/j2+cCT/B63rge2mULaqnib2OX7DVLUVksTlqvMab",
    }


def get_importmap() -> str:
    """Get the importmap for GraphiQL."""
    # Note that changing the versions here will break integrity checks! Regenerate: https://www.srihash.org/
    react = "https://esm.sh/react@19.1.0"
    react_jsx = "https://esm.sh/react@19.1.0/jsx-runtime"
    react_dom = "https://esm.sh/react-dom@19.1.0"
    react_dom_client = "https://esm.sh/react-dom@19.1.0/client"
    graphiql = "https://esm.sh/graphiql@5.0.3?standalone&external=react,react-dom,@graphiql/react,graphql"
    explorer = "https://esm.sh/@graphiql/plugin-explorer@5.0.0?standalone&external=react,@graphiql/react,graphql"
    graphiql_react = "https://esm.sh/@graphiql/react@0.35.4?standalone&external=react,react-dom,graphql"
    graphiql_toolkit = "https://esm.sh/@graphiql/toolkit@0.11.3?standalone&external=graphql"
    graphql = "https://esm.sh/graphql@16.11.0"
    json_worker = "https://esm.sh/monaco-editor@0.52.2/esm/vs/language/json/json.worker.js?worker"
    editor_worker = "https://esm.sh/monaco-editor@0.52.2/esm/vs/editor/editor.worker.js?worker"
    graphql_worker = "https://esm.sh/monaco-graphql@1.7.1/esm/graphql.worker.js?worker"

    importmap = {
        "imports": {
            "react": react,
            "react/jsx-runtime": react_jsx,
            "react-dom": react_dom,
            "react-dom/client": react_dom_client,
            "graphiql": graphiql,
            "@graphiql/plugin-explorer": explorer,
            "@graphiql/react": graphiql_react,
            "@graphiql/toolkit": graphiql_toolkit,
            "graphql": graphql,
            "monaco-editor/json-worker": json_worker,
            "monaco-editor/editor-worker": editor_worker,
            "monaco-graphql/graphql-worker": graphql_worker,
        },
        "integrity": {
            react: "sha384-C3ApUaeHIj1v0KX4cY/+K3hQZ/8HcAbbmkw1gBK8H5XN4LCEguY7+A3jga11SaHF",
            react_jsx: "sha384-ISrauaZAJlw0FRGhk9DBbU+2n4Bs1mrmh1kkJ63lTmkLTXYqpWTNFkGLPcK9C9BX",
            react_dom: "sha384-CKiqgCWLo5oVMbiCv36UR0pLRrzeRKhw1jFUpx0j/XdZOpZ43zOHhjf8yjLNuLEy",
            react_dom_client: "sha384-QH8CM8CiVIQ+RoTOjDp6ktXLkc0ix+qbx2mo7SSnwMeUQEoM4XJffjoSPY85X6VH",
            graphiql: "sha384-Vxuid6El2THg0+qYzVT1pHMOPQe1KZHNpxKaxqMqK4lbqokaJ0H+iKZR1zFhQzBN",
            explorer: "sha384-nrr4ZBQS9iyn0dn60BH3wtgG6YCSsQsuTPLgWDrUvvGvLvz0nE7LxnWWxEicmKHm",
            graphiql_react: "sha384-EnyV8FGnqfde43nPpmKz4yVI0VxlcwLVQe6P2r/cc24UcTmAzPU6SAabBonnSrT/",
            graphiql_toolkit: "sha384-ZsnupyYmzpNjF1Z/81zwi4nV352n4P7vm0JOFKiYnAwVGOf9twnEMnnxmxabMBXe",
            graphql: "sha384-uhRXaGfgCFqosYlwSLNd7XpDF9kcSUycv5yVbjjhH5OrE675kd0+MNIAAaSc+1Pi",
            json_worker: "sha384-8UXA1aePGFu/adc7cEQ8PPlVJityyzV0rDqM9Tjq1tiFFT0E7jIDQlOS4X431c+O",
            editor_worker: "sha384-lvRBk9hT6IKcVMAynOrBJUj/OCVkEaWBvzZdzvpPUqdrPW5bPsIBF7usVLLkQQxa",
            graphql_worker: "sha384-74lJ0Y2S6U0jkJAi5ijRRWnLiF0Fugr65EE1DVtJn/LHWmXJq9cVDFfC0eRjFkm1",
        },
    }
    return json.dumps(importmap, indent=2)
