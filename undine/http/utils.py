from __future__ import annotations

import dataclasses
import json
from asyncio import iscoroutinefunction
from collections.abc import Awaitable, Callable
from enum import StrEnum
from functools import cached_property, wraps
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, TypeAlias, overload

from django.http import HttpRequest, HttpResponse
from django.http.request import MediaType
from django.shortcuts import render

from undine.exceptions import (
    GraphQLMissingContentTypeError,
    GraphQLRequestDecodingError,
    GraphQLUnsupportedContentTypeError,
)
from undine.settings import undine_settings
from undine.typing import DjangoRequestProtocol, DjangoResponseProtocol
from undine.utils.graphql.utils import get_error_execution_result

if TYPE_CHECKING:
    from collections.abc import Iterable

    from graphql import ExecutionResult

    from undine.typing import RequestMethod

__all__ = [
    "HttpMethodNotAllowedResponse",
    "HttpUnsupportedContentTypeResponse",
    "decode_body",
    "get_preferred_response_content_type",
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
            result = get_error_execution_result(GraphQLMissingContentTypeError())
            return graphql_result_response(result, status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE, content_type=media_type)

        if not MediaType(request.content_type).match(content_type):
            result = get_error_execution_result(GraphQLUnsupportedContentTypeError(content_type=request.content_type))
            return graphql_result_response(result, status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE, content_type=media_type)

        return func(request)

    return wrapper  # type: ignore[return-value]


def render_graphiql(request: HttpRequest) -> HttpResponse:
    """Render GraphiQL."""
    return render(request, "undine/graphiql.html", context=get_graphiql_context())


class ModuleVersion(StrEnum):
    # Note that changing the versions here will break integrity checks!
    # Integrity values can be generated using the `update_import_map` management command.

    REACT = "19.1.1"
    GRAPHIQL = "5.2.0"
    EXPLORER = "5.1.1"
    GRAPHIQL_REACT = "0.37.1"
    GRAPHIQL_TOOLKIT = "0.11.3"
    GRAPHQL = "16.11.0"
    MONACO_EDITOR = "0.52.2"
    MONACO_GRAPHQL = "1.7.2"


@dataclasses.dataclass(kw_only=True)
class ModuleInfoItem:
    latest: str
    """URL to the latest version of the module."""

    version: ModuleVersion
    """Version of the module to use."""

    integrity: str
    """Subresource integrity hash for the module using the given version."""

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    @cached_property
    def url(self) -> str:
        return self.latest.replace("latest", self.version.value)  # type: ignore[arg-type]


class ModuleInfo:
    REACT = ModuleInfoItem(
        latest="https://esm.sh/react@latest",
        version=ModuleVersion.REACT,
        integrity="sha384-9OJoKubDZJQFG2UMdUOdDcnYWkODV+gH9m+SAlT9CjHa82SyzSkej2hzbO5QAMpj",
    )
    REACT_JSX_RUNTIME = ModuleInfoItem(
        latest="https://esm.sh/react@latest/jsx-runtime",
        version=ModuleVersion.REACT,
        integrity="sha384-3NEvPP3wjioeToUCcSPmCv3hnmoZaViS/8dYJK5EGgMXDyAEaoNe5lFp7FktwR6h",
    )
    REACT_DOM = ModuleInfoItem(
        latest="https://esm.sh/react-dom@latest",
        version=ModuleVersion.REACT,
        integrity="sha384-AkbP9ShtoY9QW6TG7svAPqnTjTRM/eMwSY13/zh0pDEyBLfNqUJvrfJSwQEdyMIF",
    )
    REACT_DOM_CLIENT = ModuleInfoItem(
        latest="https://esm.sh/react-dom@latest/client",
        version=ModuleVersion.REACT,
        integrity="sha384-iXvysXIHXb2s4DgTQrnYhOy/v/3MBGJKfiedt0fZ4pcaFy+cvBGgWGw82BYJxlR9",
    )
    GRAPHIQL = ModuleInfoItem(
        latest="https://esm.sh/graphiql@latest?standalone&external=react,react-dom,@graphiql/react,graphql",
        version=ModuleVersion.GRAPHIQL,
        integrity="sha384-32Vv0P2Qy9UWdE0/n9/nFmGh8tM5/vMgpAarsa+UdD6So+aS6DVBQZDIjS2lU52e",
    )
    EXPLORER = ModuleInfoItem(
        latest="https://esm.sh/@graphiql/plugin-explorer@latest?standalone&external=react,@graphiql/react,graphql",
        version=ModuleVersion.EXPLORER,
        integrity="sha384-rR9phbzRkwb/HINixBgg9De/Z/S6G9/OiRX7cVR1AKhP+2AUTfX7wmDT76y5HeSf",
    )
    GRAPHIQL_REACT = ModuleInfoItem(
        latest="https://esm.sh/@graphiql/react@latest?standalone&external=react,react-dom,graphql",
        version=ModuleVersion.GRAPHIQL_REACT,
        integrity="sha384-nmxT3c47Z+ZSy1Bz3TPMhyVKyF85pJI3+L9MK80JdALLMea2Z94RVLYeICwaoLbI",
    )
    GRAPHIQL_TOOLKIT = ModuleInfoItem(
        latest="https://esm.sh/@graphiql/toolkit@latest?standalone&external=graphql",
        version=ModuleVersion.GRAPHIQL_TOOLKIT,
        integrity="sha384-ZsnupyYmzpNjF1Z/81zwi4nV352n4P7vm0JOFKiYnAwVGOf9twnEMnnxmxabMBXe",
    )
    GRAPHQL = ModuleInfoItem(
        latest="https://esm.sh/graphql@latest",
        version=ModuleVersion.GRAPHQL,
        integrity="sha384-uhRXaGfgCFqosYlwSLNd7XpDF9kcSUycv5yVbjjhH5OrE675kd0+MNIAAaSc+1Pi",
    )
    MONACO_EDITOR_EDITOR_WORKER = ModuleInfoItem(
        latest="https://esm.sh/monaco-editor@latest/esm/vs/editor/editor.worker.js?worker",
        version=ModuleVersion.MONACO_EDITOR,
        integrity="sha384-lvRBk9hT6IKcVMAynOrBJUj/OCVkEaWBvzZdzvpPUqdrPW5bPsIBF7usVLLkQQxa",
    )
    MONACO_EDITOR_JSON_WORKER = ModuleInfoItem(
        latest="https://esm.sh/monaco-editor@latest/esm/vs/language/json/json.worker.js?worker",
        version=ModuleVersion.MONACO_EDITOR,
        integrity="sha384-8UXA1aePGFu/adc7cEQ8PPlVJityyzV0rDqM9Tjq1tiFFT0E7jIDQlOS4X431c+O",
    )
    MONACO_GRAPHQL_GRAPHQL_WORKER = ModuleInfoItem(
        latest="https://esm.sh/monaco-graphql@latest/esm/graphql.worker.js?worker",
        version=ModuleVersion.MONACO_GRAPHQL,
        integrity="sha384-Ji9h9Rhy4GB+oB6VrRLZ59jpS2ab0Q1KjJu6KmbVaoTgrTjGlyodHINJ0tDivxe4",
    )
    GRAPHIQL_CSS = ModuleInfoItem(
        latest="https://esm.sh/graphiql@latest/dist/style.css",
        version=ModuleVersion.GRAPHIQL,
        integrity="sha384-f6GHLfCwoa4MFYUMd3rieGOsIVAte/evKbJhMigNdzUf52U9bV2JQBMQLke0ua+2",
    )
    EXPLORER_CSS = ModuleInfoItem(
        latest="https://esm.sh/@graphiql/plugin-explorer@latest/dist/style.css",
        version=ModuleVersion.EXPLORER,
        integrity="sha384-vTFGj0krVqwFXLB7kq/VHR0/j2+cCT/B63rge2mULaqnib2OX7DVLUVksTlqvMab",
    )


def get_graphiql_context() -> dict[str, Any]:
    """Get the GraphiQL context."""
    return {
        "http_path": undine_settings.GRAPHQL_PATH,
        "ws_path": undine_settings.WEBSOCKET_PATH,
        "importmap": get_importmap(),
        "graphiql_css": ModuleInfo.GRAPHIQL_CSS.url,
        "explorer_css": ModuleInfo.EXPLORER_CSS.url,
        "graphiql_css_integrity": ModuleInfo.GRAPHIQL_CSS.integrity,
        "explorer_css_integrity": ModuleInfo.EXPLORER_CSS.integrity,
    }


def get_importmap() -> str:
    """Get the importmap for GraphiQL."""
    importmap = {
        "imports": {
            "react": ModuleInfo.REACT.url,
            "react/jsx-runtime": ModuleInfo.REACT_JSX_RUNTIME.url,
            "react-dom": ModuleInfo.REACT_DOM.url,
            "react-dom/client": ModuleInfo.REACT_DOM_CLIENT.url,
            "graphiql": ModuleInfo.GRAPHIQL.url,
            "@graphiql/plugin-explorer": ModuleInfo.EXPLORER.url,
            "@graphiql/react": ModuleInfo.GRAPHIQL_REACT.url,
            "@graphiql/toolkit": ModuleInfo.GRAPHIQL_TOOLKIT.url,
            "graphql": ModuleInfo.GRAPHQL.url,
            "monaco-editor/json-worker": ModuleInfo.MONACO_EDITOR_JSON_WORKER.url,
            "monaco-editor/editor-worker": ModuleInfo.MONACO_EDITOR_EDITOR_WORKER.url,
            "monaco-graphql/graphql-worker": ModuleInfo.MONACO_GRAPHQL_GRAPHQL_WORKER.url,
        },
        "integrity": {
            ModuleInfo.REACT.url: ModuleInfo.REACT.integrity,
            ModuleInfo.REACT_JSX_RUNTIME.url: ModuleInfo.REACT_JSX_RUNTIME.integrity,
            ModuleInfo.REACT_DOM.url: ModuleInfo.REACT_DOM.integrity,
            ModuleInfo.REACT_DOM_CLIENT.url: ModuleInfo.REACT_DOM_CLIENT.integrity,
            ModuleInfo.GRAPHIQL.url: ModuleInfo.GRAPHIQL.integrity,
            ModuleInfo.EXPLORER.url: ModuleInfo.EXPLORER.integrity,
            ModuleInfo.GRAPHIQL_REACT.url: ModuleInfo.GRAPHIQL_REACT.integrity,
            ModuleInfo.GRAPHIQL_TOOLKIT.url: ModuleInfo.GRAPHIQL_TOOLKIT.integrity,
            ModuleInfo.GRAPHQL.url: ModuleInfo.GRAPHQL.integrity,
            ModuleInfo.MONACO_EDITOR_JSON_WORKER.url: ModuleInfo.MONACO_EDITOR_JSON_WORKER.integrity,
            ModuleInfo.MONACO_EDITOR_EDITOR_WORKER.url: ModuleInfo.MONACO_EDITOR_EDITOR_WORKER.integrity,
            ModuleInfo.MONACO_GRAPHQL_GRAPHQL_WORKER.url: ModuleInfo.MONACO_GRAPHQL_GRAPHQL_WORKER.integrity,
        },
    }
    return json.dumps(importmap, indent=2)
