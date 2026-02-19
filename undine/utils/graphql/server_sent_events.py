from __future__ import annotations

import dataclasses
import io
from collections.abc import AsyncIterator
from functools import cached_property
from typing import TYPE_CHECKING, Any

from django.core.handlers.asgi import ASGIRequest
from graphql import GraphQLError

from undine.dataclasses import CompletedEventDC, CompletedEventSC, NextEventDC, NextEventSC
from undine.exceptions import GraphQLErrorGroup, GraphQLUnexpectedError
from undine.execution import execute_graphql_with_subscription
from undine.utils.graphql.utils import get_error_execution_result

if TYPE_CHECKING:
    from asgiref.typing import HTTPRequestEvent
    from django.contrib.auth.models import AnonymousUser, User
    from django.contrib.sessions.backends.base import SessionBase
    from django.core.files.uploadedfile import UploadedFile
    from django.http import HttpHeaders, QueryDict
    from django.http.request import MediaType
    from django.utils.datastructures import MultiValueDict
    from graphql import ExecutionResult

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol, HTTPASGIScope, RequestMethod

__all__ = [
    "SSERequest",
    "execute_graphql_sse_dc",
    "execute_graphql_sse_sc",
    "result_to_sse_dc",
]


# Distinct connections mode


async def execute_graphql_sse_dc(
    params: GraphQLHttpParams,
    request: DjangoRequestProtocol,
) -> AsyncIterator[NextEventDC | CompletedEventDC]:
    """Execute a GraphQL operation received through server-sent events in distinct connections mode."""
    stream = await execute_graphql_with_subscription(params, request)

    if not isinstance(stream, AsyncIterator):
        yield NextEventDC(data=stream.formatted)
        yield CompletedEventDC()
        return

    try:
        async for data in stream:
            yield NextEventDC(data=data.formatted)

    except GraphQLError as error:
        result = get_error_execution_result(error)
        yield NextEventDC(data=result.formatted)

    except GraphQLErrorGroup as error:
        result = get_error_execution_result(error)
        yield NextEventDC(data=result.formatted)

    except Exception as error:  # noqa: BLE001
        result = get_error_execution_result(GraphQLUnexpectedError(message=str(error)))
        yield NextEventDC(data=result.formatted)

    yield CompletedEventDC()


async def result_to_sse_dc(result: ExecutionResult) -> AsyncIterator[NextEventDC | CompletedEventDC]:  # noqa: RUF029
    """Get iterator for a single result received through server-sent events in distinct connections mode."""
    yield NextEventDC(data=result.formatted)
    yield CompletedEventDC()


# Single connections mode


async def execute_graphql_sse_sc(
    operation_id: str,
    params: GraphQLHttpParams,
    request: DjangoRequestProtocol,
) -> AsyncIterator[NextEventSC | CompletedEventSC]:
    """Execute a GraphQL operation received through server-sent events in single connection mode."""
    stream = await execute_graphql_with_subscription(params, request)

    if not isinstance(stream, AsyncIterator):
        yield NextEventSC(operation_id=operation_id, payload=stream.formatted)
        yield CompletedEventSC(operation_id=operation_id)
        return

    try:
        async for data in stream:
            yield NextEventSC(operation_id=operation_id, payload=data.formatted)

    except GraphQLError as error:
        result = get_error_execution_result(error)
        yield NextEventSC(operation_id=operation_id, payload=result.formatted)

    except GraphQLErrorGroup as error:
        result = get_error_execution_result(error)
        yield NextEventSC(operation_id=operation_id, payload=result.formatted)

    except Exception as error:  # noqa: BLE001
        result = get_error_execution_result(GraphQLUnexpectedError(message=str(error)))
        yield NextEventSC(operation_id=operation_id, payload=result.formatted)

    yield CompletedEventSC(operation_id=operation_id)


@dataclasses.dataclass(kw_only=True)  # No slots due to '@cached_property'
class SSERequest:
    """
    Wraps the messages received by Channels as a Django request.
    Importantly, this makes the middleware properties set by AuthMiddlewareStack available.
    """

    scope: HTTPASGIScope
    messages: list[HTTPRequestEvent]

    @cached_property
    def _request(self) -> ASGIRequest:
        body = b"".join(message["body"] for message in self.messages if "body" in message)
        return ASGIRequest(scope=self.scope, body_file=io.BytesIO(body))

    @property
    def GET(self) -> QueryDict:  # noqa: N802
        return self._request.GET

    @property
    def POST(self) -> QueryDict:  # noqa: N802
        return self._request.POST

    @property
    def COOKIES(self) -> dict[str, str]:  # noqa: N802
        return self._request.COOKIES

    @property
    def FILES(self) -> MultiValueDict[str, UploadedFile]:  # noqa: N802
        return self._request.FILES

    @property
    def META(self) -> dict[str, Any]:  # noqa: N802
        return self._request.META

    @property
    def scheme(self) -> str | None:
        return self._request.scheme

    @property
    def path(self) -> str:
        return self._request.path

    @property
    def method(self) -> RequestMethod:
        return self._request.method  # type: ignore[return-value]

    @property
    def headers(self) -> HttpHeaders:
        return self._request.headers

    @property
    def body(self) -> bytes:
        return self._request.body

    @property
    def encoding(self) -> str | None:
        return self._request.encoding

    @property
    def user(self) -> User | AnonymousUser:
        return self.scope["user"]

    async def auser(self) -> User | AnonymousUser:
        return self.user

    @property
    def session(self) -> SessionBase:
        return self.scope["session"]

    @property
    def content_type(self) -> str | None:
        return self._request.content_type

    @property
    def content_params(self) -> dict[str, str] | None:
        return self._request.content_params

    @property
    def accepted_types(self) -> list[MediaType]:
        return self._request.accepted_types

    @property
    def response_content_type(self) -> str:
        return getattr(self, "_response_content_type", "application/json")

    @response_content_type.setter
    def response_content_type(self, value: str) -> None:
        self._response_content_type = value
