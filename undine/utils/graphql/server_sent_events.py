from __future__ import annotations

import dataclasses
import io
import json
import uuid
from collections.abc import AsyncIterator
from functools import cached_property, wraps
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from asgiref.typing import HTTPResponseBodyEvent, HTTPResponseStartEvent
from django.core.handlers.asgi import ASGIRequest
from django.http import HttpResponse
from graphql import GraphQLError

from undine.dataclasses import CompletedEventDC, CompletedEventSC, NextEventDC, NextEventSC
from undine.exceptions import (
    ContinueConsumer,
    GraphQLErrorGroup,
    GraphQLSSEOperationAlreadyExistsError,
    GraphQLSSEOperationIdMissingError,
    GraphQLSSESingleConnectionNotAuthenticatedError,
    GraphQLSSEStreamAlreadyOpenError,
    GraphQLSSEStreamAlreadyRegisteredError,
    GraphQLSSEStreamNotFoundError,
    GraphQLSSEStreamTokenMissingError,
    GraphQLUnexpectedError,
)
from undine.execution import execute_graphql_with_subscription
from undine.http.utils import (
    HttpMethodNotAllowedResponse,
    HttpUnsupportedContentTypeResponse,
    get_graphql_event_stream_token,
)
from undine.parsers import GraphQLRequestParamsParser
from undine.settings import undine_settings
from undine.typing import DjangoRequestProtocol, SSEState
from undine.utils.graphql.utils import get_error_execution_result

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from asgiref.typing import HTTPRequestEvent
    from django.contrib.auth.models import AnonymousUser, User
    from django.contrib.sessions.backends.base import SessionBase
    from django.core.files.uploadedfile import UploadedFile
    from django.http import HttpHeaders, QueryDict
    from django.http.request import MediaType
    from django.utils.datastructures import MultiValueDict
    from graphql import ExecutionResult

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol, HTTPASGIScope, P, RequestMethod, SSEProtocol

__all__ = [
    "GraphQLOverSSESingleConnectionHandler",
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
        yield NextEventSC(operation_id=operation_id, data=stream.formatted)
        yield CompletedEventSC(operation_id=operation_id)
        return

    try:
        async for data in stream:
            yield NextEventSC(operation_id=operation_id, data=data.formatted)

    except GraphQLError as error:
        result = get_error_execution_result(error)
        yield NextEventSC(operation_id=operation_id, data=result.formatted)

    except GraphQLErrorGroup as error:
        result = get_error_execution_result(error)
        yield NextEventSC(operation_id=operation_id, data=result.formatted)

    except Exception as error:  # noqa: BLE001
        result = get_error_execution_result(GraphQLUnexpectedError(message=str(error)))
        yield NextEventSC(operation_id=operation_id, data=result.formatted)

    yield CompletedEventSC(operation_id=operation_id)


# Single connection mode handler


def raised_exceptions_to_responses(func: Callable[P, Awaitable[None]]) -> Callable[P, Awaitable[None]]:
    """Wraps raised exceptions as GraphQL responses if they happen in the handler."""

    @wraps(func)
    async def wrapper(self: GraphQLOverSSESingleConnectionHandler, *args: P.args, **kwargs: P.kwargs) -> None:
        try:
            return await func(self, *args, **kwargs)

        except GraphQLError as error:
            await self.send_graphql_error_response(error)
            return None

        except GraphQLErrorGroup as error:
            await self.send_graphql_error_response(error)
            return None

        except ContinueConsumer:
            raise

        except Exception as error:  # noqa: BLE001
            await self.send_graphql_error_response(GraphQLUnexpectedError(message=str(error)))
            return None

    return wrapper  # type: ignore[return-value]


@dataclasses.dataclass(kw_only=True, slots=True)
class GraphQLOverSSESingleConnectionHandler:
    """Handler for GraphQL over Server-Sent Events single connection mode."""

    sse: SSEProtocol

    @raised_exceptions_to_responses
    async def receive(self, request: DjangoRequestProtocol) -> None:
        """Process a GraphQL over SSE request."""
        if not request.user.is_authenticated:
            raise GraphQLSSESingleConnectionNotAuthenticatedError

        match request.method:
            case "PUT":
                if not any(a.match("text/plain") for a in request.accepted_types):
                    response = HttpUnsupportedContentTypeResponse(supported_types=["text/plain"])
                    await self.send_http_response(response)
                    return

                request.response_content_type = "text/plain"
                await self.reserve_event_stream(request)

            case "GET" | "POST":
                if any(a.main_type == "text" and a.sub_type == "event-stream" for a in request.accepted_types):
                    request.response_content_type = "text/event-stream"
                    await self.start_event_stream(request)
                    return

                request.response_content_type = "text/plain"
                await self.start_operation(request)

            case "DELETE":
                request.response_content_type = "text/plain"
                await self.cancel_subscription(request)

            case _:
                response = HttpMethodNotAllowedResponse(allowed_methods=["GET", "POST", "PUT", "DELETE"])
                await self.send_http_response(response)

    # Handlers

    async def reserve_event_stream(self, request: DjangoRequestProtocol) -> None:
        """Handle the 'PUT' request to reserve an event stream."""
        stream_token_key = get_sse_stream_token_key()
        stream_state_key = get_sse_stream_state_key()

        session_stream_token: str | None = await request.session.aget(stream_token_key)

        if session_stream_token is not None:
            session_stream_state: SSEState | None = await request.session.aget(stream_state_key)
            if session_stream_state != SSEState.OPENED:
                raise GraphQLSSEStreamAlreadyRegisteredError

            await self.clean_up_session(request)

        stream_token = uuid.uuid4().hex

        await request.session.aset(key=stream_token_key, value=stream_token)
        await request.session.aset(key=stream_state_key, value=SSEState.REGISTERED.value)
        await request.session.asave()

        response = HttpResponse(content=stream_token, content_type="text/plain", status=HTTPStatus.CREATED)
        await self.send_http_response(response)

    async def start_event_stream(self, request: DjangoRequestProtocol) -> None:
        """Handle the 'GET' or 'POST' request to start the event stream."""
        stream_token = get_graphql_event_stream_token(request)
        if not stream_token:
            raise GraphQLSSEStreamTokenMissingError

        stream_token_key = get_sse_stream_token_key()
        stream_state_key = get_sse_stream_state_key()

        session_stream_token: str | None = await request.session.aget(stream_token_key)
        session_stream_state: SSEState | None = await request.session.aget(stream_state_key)

        if stream_token != session_stream_token:
            raise GraphQLSSEStreamNotFoundError
        if session_stream_state == SSEState.OPENED:
            raise GraphQLSSEStreamAlreadyOpenError

        await request.session.aset(key=stream_state_key, value=SSEState.OPENED.value)
        await request.session.asave()

        headers: dict[str, str] = {
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Content-Encoding": "none",
            "Content-Type": "text/event-stream; charset=utf-8",
        }

        await self.send_headers(status=HTTPStatus.OK, headers=headers)
        await self.send_body(body="", more_body=True)

        await self.sse.start_stream(stream_token=stream_token)

    async def stop_event_stream(self, request: DjangoRequestProtocol, stream_token: str) -> None:
        """Handle stopping the event stream on disconnect."""
        # Reload session to ensure it is up to date.
        await request.session.aload()

        stream_token_key = get_sse_stream_token_key()
        session_stream_token: str | None = await request.session.aget(stream_token_key)

        # If the current stream token matches the one being stopped, clean up.
        if session_stream_token == stream_token:
            await self.clean_up_session(request)
            await request.session.asave()

        await self.send_body(body="", more_body=False)

    async def start_operation(self, request: DjangoRequestProtocol) -> None:
        """Handle the 'GET' or 'POST' request to add an operation to the event stream."""
        stream_token = get_graphql_event_stream_token(request)
        if not stream_token:
            raise GraphQLSSEStreamTokenMissingError

        stream_token_key = get_sse_stream_token_key()
        stream_state_key = get_sse_stream_state_key()

        session_stream_token: str | None = await request.session.aget(stream_token_key)
        session_stream_state: SSEState | None = await request.session.aget(stream_state_key)

        if session_stream_token != stream_token or session_stream_state != SSEState.OPENED:
            raise GraphQLSSEStreamNotFoundError

        params = GraphQLRequestParamsParser.run(request)

        operation_id = params.extensions.get("operationId")
        if not operation_id:
            raise GraphQLSSEOperationIdMissingError

        stream_operation_key = get_sse_operation_key(operation_id=operation_id)

        if await request.session.aget(key=stream_operation_key) is not None:
            raise GraphQLSSEOperationAlreadyExistsError

        await request.session.aset(key=stream_operation_key, value=True)
        await request.session.asave()

        response = HttpResponse(content="", content_type="text/plain", status=HTTPStatus.ACCEPTED)
        await self.send_http_response(response)

        await self.sse.run_operation(stream_token=stream_token, operation_id=operation_id, params=params)

    async def complete_operation(self, request: DjangoRequestProtocol, operation_id: str) -> None:
        """Clean up session state for a completed operation."""
        # Reload session to ensure it is up to date.
        await request.session.aload()

        stream_token_key = get_sse_stream_token_key()
        session_stream_token: str | None = await request.session.aget(stream_token_key)

        # If stream has already been closed, don't override with stale data.
        if session_stream_token is None:
            return

        stream_operation_key = get_sse_operation_key(operation_id=operation_id)
        await request.session.apop(key=stream_operation_key, default=None)
        await request.session.asave()

    async def cancel_subscription(self, request: DjangoRequestProtocol) -> None:
        """Handle the 'DELETE' request to cancel an operation in the event stream."""
        stream_token = get_graphql_event_stream_token(request)
        if not stream_token:
            raise GraphQLSSEStreamTokenMissingError

        operation_id = request.GET.get("operationId")
        if not operation_id:
            raise GraphQLSSEOperationIdMissingError

        stream_token_key = get_sse_stream_token_key()
        stream_state_key = get_sse_stream_state_key()

        session_stream_token: str | None = await request.session.aget(stream_token_key)
        session_stream_state: SSEState | None = await request.session.aget(stream_state_key)

        if session_stream_token != stream_token or session_stream_state != SSEState.OPENED:
            raise GraphQLSSEStreamNotFoundError

        await self.sse.cancel_operation(stream_token=stream_token, operation_id=operation_id)

        response = HttpResponse(content="", content_type="text/plain", status=HTTPStatus.OK)
        await self.send_http_response(response)

    # Session helpers

    async def clean_up_session(self, request: DjangoRequestProtocol) -> None:
        stream_token_key = get_sse_stream_token_key()
        stream_state_key = get_sse_stream_state_key()

        await request.session.apop(key=stream_token_key, default=None)
        await request.session.apop(key=stream_state_key, default=None)

        operation_prefix = get_sse_operation_key(operation_id="")
        for key in list(request.session.keys()):
            if key.startswith(operation_prefix):
                await request.session.apop(key=key, default=None)

    # High-level interface

    async def send_http_response(self, response: HttpResponse) -> None:
        await self.send_single_response(
            body=response.content.decode("utf-8"),
            status=HTTPStatus(response.status_code),
            headers=dict(response.headers),
        )

    async def send_graphql_error_response(self, error: GraphQLError | GraphQLErrorGroup) -> None:
        result = get_error_execution_result(error)
        status = HTTPStatus.INTERNAL_SERVER_ERROR
        if isinstance(error, GraphQLError) and error.extensions:
            status = error.extensions.get("status_code", status)
        await self.send_single_response(
            body=json.dumps(result.formatted, separators=(",", ":")),
            status=status,
            headers={"Content-Type": "application/json"},
        )

    async def send_single_response(
        self,
        body: str,
        status: HTTPStatus = HTTPStatus.OK,
        headers: dict[str, Any] | None = None,
    ) -> None:
        await self.send_headers(status=status, headers=headers)
        await self.send_body(body=body)

    # Low-level interface

    async def send_headers(self, *, status: HTTPStatus, headers: dict[str, Any] | None = None) -> None:
        headers = {key.title(): value for key, value in (headers or {}).items()}
        headers_array = [(bytes(key, "ascii"), bytes(value, "latin1")) for key, value in headers.items()]

        await self.sse.send(
            HTTPResponseStartEvent(
                type="http.response.start",
                status=status,
                headers=headers_array,
                trailers=False,
            ),
        )

    async def send_body(self, *, body: str, more_body: bool = False) -> None:
        await self.sse.send(
            HTTPResponseBodyEvent(
                type="http.response.body",
                body=body.encode("utf-8"),
                more_body=more_body,
            ),
        )


def get_sse_stream_token_key() -> str:
    return f"{undine_settings.SSE_STREAM_SESSION_PREFIX}|token"


def get_sse_stream_state_key() -> str:
    return f"{undine_settings.SSE_STREAM_SESSION_PREFIX}|state"


def get_sse_operation_key(*, operation_id: str) -> str:
    return f"{undine_settings.SSE_STREAM_SESSION_PREFIX}|operation|{operation_id}"


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
