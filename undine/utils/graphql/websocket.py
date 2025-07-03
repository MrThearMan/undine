from __future__ import annotations

import asyncio
import dataclasses
import io
import json
from collections.abc import AsyncIterator
from contextlib import suppress
from functools import cached_property, wraps
from inspect import isawaitable
from typing import TYPE_CHECKING, Any

from asgiref.typing import WebSocketAcceptEvent, WebSocketCloseEvent, WebSocketSendEvent
from django.core.handlers.asgi import ASGIRequest
from graphql import GraphQLError

from undine.exceptions import (
    GraphQLErrorGroup,
    GraphQLUnexpectedError,
    WebSocketConnectionInitAlreadyInProgressError,
    WebSocketConnectionInitForbiddenError,
    WebSocketConnectionInitTimeoutError,
    WebSocketEmptyMessageError,
    WebSocketError,
    WebSocketInternalServerError,
    WebSocketInvalidCompleteMessageOperationIdError,
    WebSocketInvalidConnectionInitPayloadError,
    WebSocketInvalidJSONError,
    WebSocketInvalidPingPayloadError,
    WebSocketInvalidPongPayloadError,
    WebSocketInvalidSubscribeOperationIdError,
    WebSocketInvalidSubscribePayloadError,
    WebSocketMissingCompleteMessageOperationIdError,
    WebSocketMissingSubscribeOperationIdError,
    WebSocketMissingSubscribePayloadError,
    WebSocketSubscriberForOperationIdAlreadyExistsError,
    WebSocketTooManyInitialisationRequestsError,
    WebSocketTypeMissingError,
    WebSocketUnauthorizedError,
    WebSocketUnknownMessageTypeError,
    WebSocketUnsupportedSubProtocolError,
)
from undine.execution import execute_graphql_websocket
from undine.parsers import GraphQLRequestParamsParser
from undine.settings import undine_settings
from undine.typing import CompleteMessage, ConnectionAckMessage, ErrorMessage, NextMessage, PongMessage

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from django.contrib.auth.models import AnonymousUser, User
    from django.contrib.sessions.backends.base import SessionBase
    from django.core.files.uploadedfile import UploadedFile
    from django.http import HttpHeaders, QueryDict
    from django.http.request import MediaType
    from django.utils.datastructures import MultiValueDict
    from graphql import ExecutionResult

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import (
        ClientMessage,
        ConnectionInitMessage,
        DjangoRequestProtocol,
        GraphQLWebSocketCloseCode,
        P,
        PingMessage,
        RequestMethod,
        ServerMessage,
        SubscribeMessage,
        WebSocketASGIScope,
        WebSocketProtocol,
    )


__all__ = [
    "GRAPHQL_TRANSPORT_WS_PROTOCOL",
    "GraphQLOverWebSocketHandler",
    "WebSocketOperation",
    "WebSocketRequest",
]


GRAPHQL_TRANSPORT_WS_PROTOCOL = "graphql-transport-ws"


def close_websocket_on_error(func: Callable[P, Awaitable[None]]) -> Callable[P, Awaitable[None]]:
    """Close websockets if exceptions are raised."""

    @wraps(func)
    async def wrapper(self: GraphQLOverWebSocketHandler, *args: P.args, **kwargs: P.kwargs) -> None:
        try:
            await func(self, *args, **kwargs)  # type: ignore[arg-type]

        except WebSocketError as error:
            await self.disconnect()
            await self.close(code=error.code, reason=error.reason)

        except Exception:  # noqa: BLE001  # pragma: no cover
            err = WebSocketInternalServerError
            await self.disconnect()
            await self.close(code=err.code, reason=err.reason)

    return wrapper  # type: ignore[return-value]


@dataclasses.dataclass(kw_only=True, slots=True)
class GraphQLOverWebSocketHandler:
    """
    Handler for the GraphQL over WebSocket Protocol.
    See: https://github.com/graphql/graphql-over-http/blob/main/rfcs/GraphQLOverWebSocket.md
    """

    websocket: WebSocketProtocol

    connection_init_timeout_task: asyncio.Task | None = None
    connection_init_timed_out: bool = False
    connection_init_received: bool = False
    connection_acknowledged: bool = False

    operations: dict[str, WebSocketOperation] = dataclasses.field(default_factory=dict)

    # Core methods

    @close_websocket_on_error
    async def connect(self) -> None:
        """Websocket created, start waiting for a connection init message."""
        if GRAPHQL_TRANSPORT_WS_PROTOCOL not in self.websocket.scope["subprotocols"]:
            raise WebSocketUnsupportedSubProtocolError

        # Shouldn't happen, but just in case.
        if isinstance(self.connection_init_timeout_task, asyncio.Task):
            self.connection_init_timeout_task.cancel()
            raise WebSocketConnectionInitAlreadyInProgressError

        self.connection_init_timeout_task = asyncio.create_task(self.handle_connection_init_timeout())
        await self.accept()

    @close_websocket_on_error
    async def receive(self, data: str | None = None) -> None:
        """Process a message received from the websocket."""
        message = self.validate_message(data)

        match message["type"]:
            case "connection_init":
                self.validate_connection_init_message(message)
                await self.handle_connection_init(message)

            case "ping":
                self.validate_ping_message(message)
                await self.handle_ping(message)

            case "pong":
                self.validate_pong_message(message)
                await self.handle_pong(message)

            case "subscribe":
                self.validate_subscribe_message(message)
                await self.handle_subscribe(message)

            case "complete":
                self.validate_complete_message(message)
                await self.handle_complete(message)

            case _:
                raise WebSocketUnknownMessageTypeError(type=message["type"])

    async def disconnect(self) -> None:
        """Await all done tasks and cancel all pending tasks before closing the websocket."""
        if self.connection_init_timeout_task is not None:
            if not self.connection_init_timeout_task.done():
                self.connection_init_timeout_task.cancel()

            with suppress(BaseException):
                await self.connection_init_timeout_task

        for operation_id in list(self.operations):
            operation = self.operations.pop(operation_id)
            if not operation.task.done():
                operation.task.cancel()

            with suppress(BaseException):
                await operation.task

    async def accept(self) -> None:
        event = WebSocketAcceptEvent(type="websocket.accept", subprotocol=GRAPHQL_TRANSPORT_WS_PROTOCOL, headers=[])
        await self.websocket.send(message=event)

    async def close(self, code: GraphQLWebSocketCloseCode, reason: str) -> None:
        event = WebSocketCloseEvent(type="websocket.close", code=code, reason=reason)
        await self.websocket.send(message=event)

    async def send(self, message: ServerMessage) -> None:
        text = json.dumps(message, separators=(",", ":"))
        event = WebSocketSendEvent(type="websocket.send", text=text, bytes=None)
        await self.websocket.send(message=event)

    # Message validation

    def validate_message(self, text_data: str | None) -> ClientMessage:
        if text_data is None:
            raise WebSocketEmptyMessageError

        try:
            message = json.loads(text_data)
        except Exception as error:
            raise WebSocketInvalidJSONError from error

        if not isinstance(message, dict):
            raise WebSocketInvalidJSONError

        if "type" not in message:
            raise WebSocketTypeMissingError

        return message  # type: ignore[return-value]

    def validate_connection_init_message(self, message: ConnectionInitMessage) -> None:
        if "payload" in message and not isinstance(message["payload"], dict):
            raise WebSocketInvalidConnectionInitPayloadError

    def validate_ping_message(self, message: PingMessage) -> None:
        if "payload" in message and not isinstance(message["payload"], dict):
            raise WebSocketInvalidPingPayloadError

    def validate_pong_message(self, message: PongMessage) -> None:
        if "payload" in message and not isinstance(message["payload"], dict):
            raise WebSocketInvalidPongPayloadError

    def validate_subscribe_message(self, message: SubscribeMessage) -> None:
        if "id" not in message:
            raise WebSocketMissingSubscribeOperationIdError

        if not isinstance(message["id"], str):
            raise WebSocketInvalidSubscribeOperationIdError

        if "payload" not in message:
            raise WebSocketMissingSubscribePayloadError

        if not isinstance(message["payload"], dict):
            raise WebSocketInvalidSubscribePayloadError

    def validate_complete_message(self, message: CompleteMessage) -> None:
        if "id" not in message:
            raise WebSocketMissingCompleteMessageOperationIdError

        if not isinstance(message["id"], str):
            raise WebSocketInvalidCompleteMessageOperationIdError

    # Message handlers

    async def handle_connection_init(self, message: ConnectionInitMessage) -> None:
        """Indicates that the client wants to establish a connection within the existing socket."""
        if self.connection_init_timed_out:
            return

        if self.connection_init_timeout_task is not None:
            self.connection_init_timeout_task.cancel()

        if self.connection_init_received:
            raise WebSocketTooManyInitialisationRequestsError

        self.connection_init_received = True

        request = WebSocketRequest(scope=self.websocket.scope, message=message)
        try:
            payload = undine_settings.WEBSOCKET_CONNECTION_INIT_HOOK(request)
            if isawaitable(payload):
                payload = await payload
        except GraphQLError as error:
            raise WebSocketConnectionInitForbiddenError(reason=error.message) from error
        except Exception as error:
            raise WebSocketConnectionInitForbiddenError from error

        response = ConnectionAckMessage(type="connection_ack")
        if payload is not None:
            response["payload"] = payload

        await self.send(message=response)

        self.connection_acknowledged = True

    async def handle_connection_init_timeout(self) -> None:
        """Handle connection init timeout. Started as a task when a socket is accepted."""
        await asyncio.sleep(delay=undine_settings.WEBSOCKET_CONNECTION_INIT_TIMEOUT_SECONDS)
        if self.connection_init_received:
            return

        self.connection_init_timed_out = True

        error = WebSocketConnectionInitTimeoutError
        await self.close(code=error.code, reason=error.reason)

    async def handle_ping(self, message: PingMessage) -> None:
        """
        Useful for detecting failed connections, displaying latency metrics or other types of network probing.

        A Pong must be sent in response from the receiving party as soon as possible.
        The Ping message can be sent at any time within the established socket.
        """
        request = WebSocketRequest(scope=self.websocket.scope, message=message)
        payload = undine_settings.WEBSOCKET_PING_HOOK(request)
        if isawaitable(payload):
            payload = await payload

        response = PongMessage(type="pong")
        if payload is not None:
            response["payload"] = payload

        await self.send(message=response)

    async def handle_pong(self, message: PongMessage) -> None:
        """
        The Pong message can be sent at any time within the established socket,
        and may even be sent unsolicited as an unidirectional heartbeat.
        """
        request = WebSocketRequest(scope=self.websocket.scope, message=message)
        hook = undine_settings.WEBSOCKET_PONG_HOOK(request)
        if isawaitable(hook):
            await hook

    async def handle_subscribe(self, message: SubscribeMessage) -> None:
        """
        Request an operation specified in the message payload. This message provides a unique ID
        field to connect published messages to the operation requested by this message.
        """
        if not self.connection_acknowledged:
            raise WebSocketUnauthorizedError

        if message["id"] in self.operations:
            raise WebSocketSubscriberForOperationIdAlreadyExistsError(id=message["id"])

        try:
            params = GraphQLRequestParamsParser.get_graphql_params(message["payload"])
        except GraphQLError as error:
            raise WebSocketInvalidSubscribePayloadError(reason=error.message) from error

        self.operations[message["id"]] = WebSocketOperation(
            handler=self,
            operation_id=message["id"],
            params=params,
            request=WebSocketRequest(scope=self.websocket.scope, message=message),  # type: ignore[arg-type]
        )

    async def handle_complete(self, message: CompleteMessage) -> None:
        """
        Client has stopped listening and wants to complete the subscription.
        No further events, relevant to the original subscription, should be sent through.
        """
        operation = self.operations.get(message["id"])
        if operation is not None:
            operation.set_completed()
            operation.task.cancel()

            with suppress(BaseException):
                await operation.task


@dataclasses.dataclass(kw_only=True, slots=True)
class WebSocketOperation:
    """Encapsulates a GraphQL operation received through a WebSocket."""

    handler: GraphQLOverWebSocketHandler
    operation_id: str
    params: GraphQLHttpParams
    request: DjangoRequestProtocol

    task: asyncio.Task = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        # Operation starts executing as soon an instance is created.
        self.task = asyncio.create_task(self.run())

    @property
    def is_completed(self) -> bool:
        return self.operation_id not in self.handler.operations

    def set_completed(self) -> None:
        self.handler.operations.pop(self.operation_id, None)

    async def run(self) -> None:
        result = await execute_graphql_websocket(self.params, self.request)

        if isinstance(result, AsyncIterator):
            await self.execute_subscription(result)
            return

        await self.execute_singe_result_operation(result)

    async def execute_singe_result_operation(self, result: ExecutionResult) -> None:
        if result.errors:
            await self.send_errors(errors=result.errors)
            return

        await self.send_next(result=result)
        await self.send_complete()

    async def execute_subscription(self, source: AsyncIterator[ExecutionResult]) -> None:
        initial = True
        try:
            async for result in source:
                if initial and result.errors:
                    await self.send_errors(errors=result.errors)
                    return

                initial = False
                await self.send_next(result=result)

        except GraphQLError as error:
            await self.send_errors(errors=[error])

        except GraphQLErrorGroup as error:
            await self.send_errors(errors=list(error.flatten()))

        except Exception as error:  # noqa: BLE001
            await self.send_errors(errors=[GraphQLUnexpectedError(message=str(error))])

        else:
            await self.send_complete()

    async def send_errors(self, errors: list[GraphQLError]) -> None:
        """
        Operation execution error(s) in response to the Subscribe message.
        This can occur before execution starts, usually due to validation errors,
        or during the execution of the request. This message terminates the operation
        and no further messages will be sent.
        """
        if self.is_completed:  # pragma: no cover
            return

        error_payload = [err.formatted for err in errors]
        error_message = ErrorMessage(type="error", id=self.operation_id, payload=error_payload)
        await self.handler.send(error_message)

        self.set_completed()

    async def send_next(self, result: ExecutionResult) -> None:
        """
        Operation execution result(s) from the source stream created by the binding Subscribe message.
        After all results have been emitted, the Complete message will follow indicating stream completion.
        """
        if self.is_completed:  # pragma: no cover
            return

        next_message = NextMessage(type="next", id=self.operation_id, payload=result.formatted)
        await self.handler.send(next_message)

    async def send_complete(self) -> None:
        """The requested operation execution has completed."""
        if self.is_completed:  # pragma: no cover
            return

        complete_message = CompleteMessage(type="complete", id=self.operation_id)
        await self.handler.send(complete_message)

        self.set_completed()


@dataclasses.dataclass(kw_only=True)  # No slots due to '@cached_property'
class WebSocketRequest:
    """Imitate a Django HttpRequest object from a WebSocket connection."""

    scope: WebSocketASGIScope
    message: ConnectionInitMessage | PingMessage | PongMessage | SubscribeMessage

    @cached_property
    def _request(self) -> ASGIRequest:
        body = json.dumps(self.message["payload"]).encode("utf-8")
        # Method is not technically part of WebSocketASGIScope,
        # but needs to be set for ASGIRequest to initialize correctly.
        self.scope["method"] = "WEBSOCKET"  # type: ignore[typeddict-unknown-key]
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
        return "application/json"

    @response_content_type.setter
    def response_content_type(self, value: str) -> None: ...


# Default hooks


def connection_init_hook(request: WebSocketRequest) -> dict[str, Any] | None:
    """Default hook for custom connection init handling."""


def ping_hook(request: WebSocketRequest) -> dict[str, Any] | None:
    """Default hook for custom ping handling."""


def pong_hook(request: WebSocketRequest) -> None:
    """Default hook for custom pong handling."""
