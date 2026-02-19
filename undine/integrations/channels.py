from __future__ import annotations

import asyncio
import functools
import hashlib
import io
import json
import uuid
from abc import ABC, abstractmethod
from contextlib import suppress
from functools import cached_property
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from asgiref.typing import HTTPResponseBodyEvent, HTTPResponseStartEvent
from channels.auth import AuthMiddlewareStack
from channels.consumer import AsyncConsumer
from channels.db import aclose_old_connections
from channels.exceptions import InvalidChannelLayerError, StopConsumer
from channels.layers import get_channel_layer
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from channels.utils import await_many_dispatch
from django.core.handlers.asgi import ASGIRequest
from django.http import HttpResponse
from django.urls import re_path
from graphql import GraphQLError

from undine.dataclasses import CompletedEventSC
from undine.exceptions import (
    ContinueConsumer,
    GraphQLErrorGroup,
    GraphQLSSEOperationAlreadyExistsError,
    GraphQLSSEOperationIdMissingError,
    GraphQLSSESingleConnectionNotAuthenticatedError,
    GraphQLSSEStreamAlreadyOpenError,
    GraphQLSSEStreamNotFoundError,
    GraphQLSSEStreamNotOpenError,
    GraphQLSSEStreamTokenMissingError,
    GraphQLUnexpectedError,
)
from undine.http.utils import (
    HttpMethodNotAllowedResponse,
    HttpUnsupportedContentTypeResponse,
    get_graphql_event_stream_token,
)
from undine.parsers import GraphQLRequestParamsParser
from undine.settings import undine_settings
from undine.typing import SSEOperationCancelEvent, SSEOperationResultEvent, SSEState, SSEStreamCloseEvent
from undine.utils.graphql.server_sent_events import SSERequest, execute_graphql_sse_sc
from undine.utils.graphql.utils import get_error_execution_result
from undine.utils.graphql.websocket import GraphQLOverWebSocketHandler

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from asgiref.typing import (
        ASGI3Application,
        ASGIReceiveCallable,
        ASGISendCallable,
        HTTPDisconnectEvent,
        HTTPRequestEvent,
        WebSocketConnectEvent,
        WebSocketDisconnectEvent,
        WebSocketReceiveEvent,
    )
    from channels.layers import BaseChannelLayer
    from django.core.handlers.asgi import ASGIHandler

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol, HTTPASGIScope

__all__ = [
    "get_sse_enabled_app",
    "get_websocket_and_sse_enabled_app",
    "get_websocket_enabled_app",
]


# App wrappers


def get_websocket_enabled_app(django_application: ASGIHandler) -> Any:  # pragma: no cover
    """
    Create the default routing configuration for supporting GraphQL over WebSocket.

    >>> # asgi.py
    >>> import os
    >>>
    >>> from django.core.asgi import get_asgi_application
    >>>
    >>> os.environ.setdefault("DJANGO_SETTINGS_MODULE", "...")
    >>> django_application = get_asgi_application()
    >>>
    >>> # Needs to be imported after 'django_application' is created!
    >>> from undine.integrations.channels import get_websocket_enabled_app
    >>>
    >>> application = get_websocket_enabled_app(django_application)
    """
    websocket_urlpatterns = [re_path(undine_settings.WEBSOCKET_PATH, GraphQLWebSocketConsumer.as_asgi())]

    return ProtocolTypeRouter({
        "http": django_application,
        "websocket": AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(websocket_urlpatterns))),
    })


def get_sse_enabled_app(django_application: ASGIHandler) -> Any:  # pragma: no cover
    """
    Create the default routing configuration for supporting GraphQL over Server-Sent Events.
    Onlt required when using the single connection mode.

    >>> # asgi.py
    >>> import os
    >>>
    >>> from django.core.asgi import get_asgi_application
    >>>
    >>> os.environ.setdefault("DJANGO_SETTINGS_MODULE", "...")
    >>> django_application = get_asgi_application()
    >>>
    >>> # Needs to be imported after 'django_application' is created!
    >>> from undine.integrations.channels import get_sse_enabled_app
    >>>
    >>> application = get_sse_enabled_app(django_application)
    """
    return GraphQLSSERouter(django_application=django_application)


def get_websocket_and_sse_enabled_app(django_application: ASGIHandler) -> Any:  # pragma: no cover
    """
    Create the default routing configuration for supporting GraphQL over WebSocket and SSE.

    >>> # asgi.py
    >>> import os
    >>>
    >>> from django.core.asgi import get_asgi_application
    >>>
    >>> os.environ.setdefault("DJANGO_SETTINGS_MODULE", "...")
    >>> django_application = get_asgi_application()
    >>>
    >>> # Needs to be imported after 'django_application' is created!
    >>> from undine.integrations.channels import get_websocket_and_sse_enabled_app
    >>>
    >>> application = get_websocket_and_sse_enabled_app(django_application)
    """
    websocket_urlpatterns = [re_path(undine_settings.WEBSOCKET_PATH, GraphQLWebSocketConsumer.as_asgi())]

    return ProtocolTypeRouter({
        "http": get_sse_enabled_app(django_application),
        "websocket": AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(websocket_urlpatterns))),
    })


# Websockets


class GraphQLWebSocketConsumer(AsyncConsumer):
    """Channels consumer receiving messages from the WebSocket for the GraphQL over WebSocket Protocol."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.handler = GraphQLOverWebSocketHandler(websocket=self)

    async def websocket_connect(self, message: WebSocketConnectEvent) -> None:
        await self.handler.connect()

    async def websocket_receive(self, message: WebSocketReceiveEvent) -> None:
        await self.handler.receive(data=message["text"])

    async def websocket_disconnect(self, message: WebSocketDisconnectEvent) -> None:
        await self.handler.disconnect()
        await aclose_old_connections()
        raise StopConsumer


# SSE (consumers)


class SSEConsumerSendingMixin:
    """Bundles sending helpers for consumers."""

    send: ASGISendCallable

    async def send_http_response(self, *, response: HttpResponse) -> None:
        await self.send_single_response(
            body=response.content.decode("utf-8"),
            status=HTTPStatus(response.status_code),
            headers=dict(response.headers),
        )

    async def send_graphql_error_response(self, *, error: GraphQLError | GraphQLErrorGroup) -> None:
        result = get_error_execution_result(error)
        status = HTTPStatus.INTERNAL_SERVER_ERROR
        if isinstance(error, GraphQLError) and error.extensions:
            status = error.extensions.get("status_code", status)

        await self.send_single_response(
            body=json.dumps(result.formatted, separators=(",", ":")),
            status=status,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

    async def send_single_response(
        self,
        *,
        body: str,
        status: HTTPStatus = HTTPStatus.OK,
        headers: dict[str, Any] | None = None,
    ) -> None:
        await self.send_headers(status=status, headers=headers)
        await self.send_body(body=body)

    async def send_headers(self, *, status: HTTPStatus, headers: dict[str, Any] | None = None) -> None:
        headers = {key.title(): value for key, value in (headers or {}).items()}
        headers_array = [(bytes(key, "ascii"), bytes(value, "latin1")) for key, value in headers.items()]

        await self.send(
            HTTPResponseStartEvent(
                type="http.response.start",
                status=status,
                headers=headers_array,
                trailers=False,
            ),
        )

    async def send_body(self, *, body: str, more_body: bool = False) -> None:
        await self.send(
            HTTPResponseBodyEvent(
                type="http.response.body",
                body=body.encode("utf-8"),
                more_body=more_body,
            ),
        )


class SSEConsumerSessionMixin:
    """Bundles session helpers for consumers."""

    request: DjangoRequestProtocol

    # Low level interface

    async def refresh_session(self) -> None:
        """Force load of the session data form the session store and cache it."""
        with suppress(AttributeError):
            del self.request.session._session_cache  # noqa: SLF001
        await self.request.session._aget_session()  # noqa: SLF001

    async def save_session(self) -> None:
        """Save the session data to the session store."""
        await self.request.session.asave()

    def set_in_session(self, *, key: str, value: str) -> None:
        """Set a value in the session data. Must call `refresh_session` before using."""
        self.request.session[key] = value

    def get_from_session(self, *, key: str) -> str | None:
        """Get a value from the session data. Must call `refresh_session` before using."""
        return self.request.session.get(key)

    def delete_from_session(self, *, key: str) -> None:
        """Delete a value from the session data. Must call `refresh_session` before using."""
        self.request.session.pop(key, None)

    def is_in_session(self, *, key: str) -> bool:
        """Check if a value is in the session data. Must call `refresh_session` before using."""
        return key in self.request.session

    # Stream token

    def get_session_stream_token(self) -> str | None:
        stream_token_key = get_sse_stream_token_key()
        return self.get_from_session(key=stream_token_key)

    def set_session_stream_token(self, *, stream_token: str) -> None:
        stream_token_key = get_sse_stream_token_key()
        self.set_in_session(key=stream_token_key, value=stream_token)

    def delete_session_stream_token(self) -> None:
        stream_token_key = get_sse_stream_token_key()
        self.delete_from_session(key=stream_token_key)

    def has_session_stream_token(self) -> bool:
        stream_token_key = get_sse_stream_token_key()
        return self.is_in_session(key=stream_token_key)

    # Stream state

    def get_session_stream_state(self) -> SSEState | None:
        stream_state_key = get_sse_stream_state_key()
        return self.get_from_session(key=stream_state_key)

    def set_session_stream_state(self, *, state: SSEState) -> None:
        stream_state_key = get_sse_stream_state_key()
        self.set_in_session(key=stream_state_key, value=state.value)

    def delete_session_stream_state(self) -> None:
        stream_state_key = get_sse_stream_state_key()
        self.delete_from_session(key=stream_state_key)

    def has_session_stream_state(self) -> bool:
        stream_state_key = get_sse_stream_state_key()
        return self.is_in_session(key=stream_state_key)

    # Operation

    def get_session_operation(self, *, operation_id: str) -> str | None:
        operation_key = get_sse_operation_key(operation_id=operation_id)
        return self.get_from_session(key=operation_key)

    def set_session_operation(self, *, operation_id: str) -> None:
        operation_key = get_sse_operation_key(operation_id=operation_id)
        self.set_in_session(key=operation_key, value=operation_id)

    def delete_session_operation(self, *, operation_id: str) -> None:
        operation_key = get_sse_operation_key(operation_id=operation_id)
        self.delete_from_session(key=operation_key)

    def has_session_operation(self, *, operation_id: str) -> bool:
        operation_key = get_sse_operation_key(operation_id=operation_id)
        return self.is_in_session(key=operation_key)

    async def delete_session_all_operations(self) -> None:
        operation_prefix = get_sse_operation_key(operation_id="")
        for key in list(self.request.session.keys()):
            if key.startswith(operation_prefix):
                self.delete_from_session(key=key)


class SSEConsumerChannelLayerMixin:
    """Bundles channel layer helpers for consumers."""

    channel_layer: BaseChannelLayer
    channel_name: str

    # Sending

    async def signal_close_stream(self, *, stream_token: str) -> None:
        stream_group_name = get_stream_group_name(stream_token)
        event = SSEStreamCloseEvent(type="sse.stream.close")
        await self.channel_layer.group_send(group=stream_group_name, message=event)

    async def signal_operation_event(self, *, stream_token: str, event: str) -> None:
        stream_group_name = get_stream_group_name(stream_token)
        message = SSEOperationResultEvent(type="sse.operation.event", event=event)
        await self.channel_layer.group_send(group=stream_group_name, message=message)

    async def signal_cancel_operation(self, *, stream_token: str, operation_id: str) -> None:
        operation_group_name = get_operation_group_name(stream_token, operation_id)
        event = SSEOperationCancelEvent(type="sse.operation.cancel")
        await self.channel_layer.group_send(group=operation_group_name, message=event)

    async def signal_cancel_all_operations(self, *, stream_token: str) -> None:
        all_operations_group_name = get_all_operations_group_name(stream_token)
        event = SSEOperationCancelEvent(type="sse.operation.cancel")
        await self.channel_layer.group_send(group=all_operations_group_name, message=event)

    # Group registration

    async def register_stream(self, *, stream_token: str) -> None:
        stream_group_name = get_stream_group_name(stream_token)
        await self.channel_layer.group_add(group=stream_group_name, channel=self.channel_name)

    async def register_operation(self, *, stream_token: str, operation_id: str) -> None:
        operation_group_name = get_operation_group_name(stream_token, operation_id)
        all_operations_group_name = get_all_operations_group_name(stream_token)
        await self.channel_layer.group_add(group=operation_group_name, channel=self.channel_name)
        await self.channel_layer.group_add(group=all_operations_group_name, channel=self.channel_name)

    # Group unregistration

    async def unregister_stream(self, *, stream_token: str) -> None:
        stream_group_name = get_stream_group_name(stream_token)
        await self.channel_layer.group_discard(group=stream_group_name, channel=self.channel_name)

    async def unregister_operation(self, *, stream_token: str, operation_id: str) -> None:
        operation_group_name = get_operation_group_name(stream_token, operation_id)
        all_operations_group_name = get_all_operations_group_name(stream_token)
        await self.channel_layer.group_discard(group=operation_group_name, channel=self.channel_name)
        await self.channel_layer.group_discard(group=all_operations_group_name, channel=self.channel_name)


class GraphQLSSESingleConnectionConsumer(
    ABC,
    SSEConsumerChannelLayerMixin,
    SSEConsumerSessionMixin,
    SSEConsumerSendingMixin,
    AsyncConsumer,
):
    """
    A consumer handling the opened event stream for
    GraphQL over Server-Sent Events in Single Connection mode.
    """

    scope: HTTPASGIScope
    base_send: ASGISendCallable
    channel_layer: BaseChannelLayer
    channel_layer_alias: str
    channel_name: str
    channel_receive: ASGIReceiveCallable

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.messages: list[HTTPRequestEvent] = []

    async def __call__(self, scope: HTTPASGIScope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        channel_layer: BaseChannelLayer | None = get_channel_layer(self.channel_layer_alias)
        if channel_layer is None:
            msg = f"No channel layer configured for alias '{self.channel_layer_alias}'"
            raise InvalidChannelLayerError(msg)

        self.scope = scope
        self.base_send = send
        self.channel_layer = channel_layer
        self.channel_name: str = await self.channel_layer.new_channel()
        self.channel_receive: ASGIReceiveCallable = functools.partial(self.channel_layer.receive, self.channel_name)

        with suppress(StopConsumer):
            await self.dispatch_loop(receive)

    async def dispatch_loop(self, receive: ASGIReceiveCallable) -> None:
        await await_many_dispatch([receive, self.channel_receive], self.dispatch)

    @cached_property
    def request(self) -> DjangoRequestProtocol:
        return SSERequest(scope=self.scope, messages=self.messages)  # type: ignore[return-value]

    # HTTP interface

    async def http_request(self, message: HTTPRequestEvent) -> None:
        self.messages.append(message)
        if message.get("more_body"):
            return

        if not self.request.user.is_authenticated:
            await self.send_graphql_error_response(error=GraphQLSSESingleConnectionNotAuthenticatedError())
            await aclose_old_connections()
            raise StopConsumer

        try:
            await self.handle()

        except ContinueConsumer:
            return

        except (GraphQLError, GraphQLErrorGroup) as error:
            await self.send_graphql_error_response(error=error)

        except Exception as error:  # noqa: BLE001
            await self.send_graphql_error_response(error=GraphQLUnexpectedError(message=str(error)))

        await self.disconnect()
        await aclose_old_connections()
        raise StopConsumer

    async def http_disconnect(self, message: HTTPDisconnectEvent) -> None:
        await self.disconnect()
        await aclose_old_connections()
        raise StopConsumer

    # Interface

    @abstractmethod
    async def handle(self) -> None:
        """Handle the incoming request."""

    async def disconnect(self) -> None:
        """Additional logic to run before the consumer is disconnected."""


class SSEStreamReservationConsumer(GraphQLSSESingleConnectionConsumer):
    """
    A consumer handling event stream reservation for
    GraphQL over Server-Sent Events in Single Connection mode.
    """

    async def handle(self) -> None:
        await self.refresh_session()

        session_stream_token = self.get_session_stream_token()
        session_stream_state = self.get_session_stream_state()

        if session_stream_token is not None and session_stream_state == SSEState.OPENED:
            await self.signal_close_stream(stream_token=session_stream_token)
            await self.delete_session_all_operations()

        stream_token = uuid.uuid4().hex

        self.set_session_stream_token(stream_token=stream_token)
        self.set_session_stream_state(state=SSEState.REGISTERED)
        await self.save_session()

        response = HttpResponse(
            content=stream_token,
            content_type="text/plain; charset=utf-8",
            status=HTTPStatus.CREATED,
        )
        await self.send_http_response(response=response)


class SSEEventStreamConsumer(GraphQLSSESingleConnectionConsumer):
    """
    A consumer handling the opened event stream for
    GraphQL over Server-Sent Events in Single Connection mode.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._stream_opened: bool = False
        self._keep_alive_task: asyncio.Task[None] | None = None

    async def dispatch_loop(self, receive: ASGIReceiveCallable) -> None:
        self._keep_alive_task = asyncio.create_task(self._keep_alive())
        try:
            await await_many_dispatch([receive, self.channel_receive], self.dispatch)
        finally:
            self._keep_alive_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._keep_alive_task

    async def _keep_alive(self) -> None:
        interval = undine_settings.SSE_KEEP_ALIVE_INTERVAL
        if not interval:
            return
        while True:
            await asyncio.sleep(interval)
            await self.send_body(body=":\n\n", more_body=True)

    # Implementation

    async def handle(self) -> None:
        stream_token = get_graphql_event_stream_token(self.request)
        if not stream_token:
            raise GraphQLSSEStreamTokenMissingError

        await self.refresh_session()

        session_stream_token = self.get_session_stream_token()
        session_stream_state = self.get_session_stream_state()

        if session_stream_token != stream_token:
            raise GraphQLSSEStreamNotFoundError

        if session_stream_state == SSEState.OPENED:
            raise GraphQLSSEStreamAlreadyOpenError

        self.set_session_stream_state(state=SSEState.OPENED)
        await self.save_session()

        await self.register_stream(stream_token=stream_token)

        headers: dict[str, str] = {
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Content-Encoding": "none",
            "Content-Type": "text/event-stream; charset=utf-8",
        }

        await self.send_headers(status=HTTPStatus.OK, headers=headers)
        await self.send_body(body=":\n\n", more_body=True)
        self._stream_opened = True

        raise ContinueConsumer

    async def disconnect(self) -> None:
        stream_token = get_graphql_event_stream_token(self.request)
        if not stream_token:
            raise GraphQLSSEStreamTokenMissingError

        await self.signal_cancel_all_operations(stream_token=stream_token)
        await self.unregister_stream(stream_token=stream_token)

        # Double check if this stream is still the current stream.
        # If it is, we can delete the stream information from the session safely.
        await self.refresh_session()
        session_stream_token = self.get_session_stream_token()
        if session_stream_token == stream_token:
            self.delete_session_stream_token()
            self.delete_session_stream_state()
            await self.save_session()

        if self._stream_opened:
            await self.send_body(body="", more_body=False)

    # Consumer group methods

    async def sse_operation_event(self, event: SSEOperationResultEvent) -> None:
        """Called to send an event to the client."""
        await self.send_body(body=event["event"], more_body=True)

    async def sse_stream_close(self, event: SSEStreamCloseEvent) -> None:
        """Called to stop the stream."""
        await self.disconnect()
        await aclose_old_connections()
        raise StopConsumer


class SSEOperationConsumer(GraphQLSSESingleConnectionConsumer):
    """
    A consumer handling adding an operation to the event stream for
    GraphQL over Server-Sent Events in Single Connection mode.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.operation: asyncio.Task | None = None

    async def dispatch_loop(self, receive: ASGIReceiveCallable) -> None:
        """
        Once the GraphQL operation task is running, monitor the channel layer for cancel messages.
        When the operation task is done, stop the consumer.
        """
        receive_task = asyncio.ensure_future(receive())
        channel_task = asyncio.ensure_future(self.channel_receive())

        wait_for: list[asyncio.Task] = []

        try:
            while True:
                if self.operation is None and receive_task.done():
                    await self.dispatch(receive_task.result())
                    receive_task = asyncio.ensure_future(receive())

                if channel_task.done():
                    await self.dispatch(channel_task.result())
                    channel_task = asyncio.ensure_future(self.channel_receive())

                if not receive_task.done():
                    wait_for.append(receive_task)

                if not channel_task.done():
                    wait_for.append(channel_task)

                if self.operation is not None:
                    wait_for.append(self.operation)

                await asyncio.wait(wait_for, return_when=asyncio.FIRST_COMPLETED)

                wait_for.clear()

                if self.operation is not None and self.operation.done():
                    with suppress(BaseException):
                        await self.operation
                    await aclose_old_connections()
                    raise StopConsumer

        finally:
            for task in (receive_task, channel_task):
                if not task.done():
                    task.cancel()
                    with suppress(BaseException):
                        await task

    # Implementation

    async def handle(self) -> None:
        stream_token = get_graphql_event_stream_token(self.request)
        if not stream_token:
            raise GraphQLSSEStreamTokenMissingError

        await self.refresh_session()

        session_stream_token = self.get_session_stream_token()
        session_stream_state = self.get_session_stream_state()

        if session_stream_token != stream_token:
            raise GraphQLSSEStreamNotFoundError

        if session_stream_state != SSEState.OPENED:
            raise GraphQLSSEStreamNotOpenError

        params = GraphQLRequestParamsParser.run(self.request)

        operation_id = params.extensions.get("operationId")
        if not operation_id:
            raise GraphQLSSEOperationIdMissingError

        if self.has_session_operation(operation_id=operation_id):
            raise GraphQLSSEOperationAlreadyExistsError

        self.set_session_operation(operation_id=operation_id)
        await self.save_session()

        response = HttpResponse(content="", content_type="text/plain; charset=utf-8", status=HTTPStatus.ACCEPTED)
        await self.send_http_response(response=response)

        await self.register_operation(stream_token=stream_token, operation_id=operation_id)

        self.operation = asyncio.create_task(self.execute(stream_token, operation_id, params))
        raise ContinueConsumer

    async def disconnect(self) -> None:
        if self.operation is not None and not self.operation.done():
            self.operation.cancel()
            with suppress(BaseException):
                await self.operation

    # Helpers

    async def execute(self, stream_token: str, operation_id: str, params: GraphQLHttpParams) -> None:
        completed: bool = False
        try:
            async for event in execute_graphql_sse_sc(operation_id, params, self.request):
                completed = completed or event.event == "complete"
                await self.signal_operation_event(stream_token=stream_token, event=event.encode())

        except asyncio.CancelledError:
            if not completed:
                event = CompletedEventSC(operation_id=operation_id)
                await self.signal_operation_event(stream_token=stream_token, event=event.encode())

        finally:
            await self.unregister_operation(stream_token=stream_token, operation_id=operation_id)

            # Double check that this stream is still open.
            # If it is, we can delete the operation from the session safely.
            await self.refresh_session()
            session_stream_token = self.get_session_stream_token()
            if session_stream_token == stream_token:
                self.delete_session_operation(operation_id=operation_id)
                await self.save_session()

    # Consumer group methods

    async def sse_operation_cancel(self, event: SSEOperationCancelEvent) -> None:
        """Called in an operation consumer to cancel its operation."""
        if self.operation is not None and not self.operation.done():
            self.operation.cancel()


class SSEOperationCancellationConsumer(GraphQLSSESingleConnectionConsumer):
    """
    A consumer handling cancelling an operation from the event stream for
    GraphQL over Server-Sent Events in Single Connection mode.
    """

    async def handle(self) -> None:
        stream_token = get_graphql_event_stream_token(self.request)
        if not stream_token:
            raise GraphQLSSEStreamTokenMissingError

        operation_id = self.request.GET.get("operationId")
        if not operation_id:
            raise GraphQLSSEOperationIdMissingError

        await self.refresh_session()

        session_stream_token = self.get_session_stream_token()
        session_stream_state = self.get_session_stream_state()

        if session_stream_token != stream_token:
            raise GraphQLSSEStreamNotFoundError

        if session_stream_state != SSEState.OPENED:
            raise GraphQLSSEStreamNotOpenError

        await self.signal_cancel_operation(stream_token=stream_token, operation_id=operation_id)

        response = HttpResponse(content="", content_type="text/plain; charset=utf-8", status=HTTPStatus.OK)
        await self.send_http_response(response=response)


# SSE (routers)


class GraphQLSSERouter:
    """
    Router that sends GraphQL over Server-Sent Events requests
    to the single connection mode handler when required.
    """

    def __init__(self, django_application: ASGI3Application) -> None:
        self.django_application: ASGI3Application = django_application
        self.sse_application: ASGI3Application = AuthMiddlewareStack(GraphQLSSEOperationRouter())

    def __call__(self, scope: HTTPASGIScope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> Awaitable[None]:
        path = scope["path"].removeprefix("/").removesuffix("/")
        graphql_path = undine_settings.GRAPHQL_PATH.removeprefix("/").removesuffix("/")

        if path != graphql_path:
            return self.django_application(scope, receive, send)

        # PUT and DELETE are exclusively single connection mode operations.
        method = scope.get("method", "")
        if method in {"PUT", "DELETE"}:
            return self.sse_application(scope, receive, send)

        # GET/POST with a stream token are single connection mode operations.
        if method in {"GET", "POST"}:
            request = ASGIRequest(scope=scope, body_file=io.BytesIO())
            if get_graphql_event_stream_token(request):
                return self.sse_application(scope, receive, send)

        # Everything else uses distinct connections mode via Django.
        # HTTP/1.1 distinct connections are blocked in the view unless
        # `USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1` is enabled.
        return self.django_application(scope, receive, send)


class GraphQLSSEOperationRouter:
    """
    Router that sends GraphQL over Server-Sent Events requests
    to the handler responsible for a specific operation.
    """

    def __init__(self) -> None:
        self.stream_reservation_consumer = SSEStreamReservationConsumer.as_asgi()
        self.event_stream_consumer = SSEEventStreamConsumer.as_asgi()
        self.operation_consumer = SSEOperationConsumer.as_asgi()
        self.operation_cancellation_consumer = SSEOperationCancellationConsumer.as_asgi()

    def __call__(self, scope: HTTPASGIScope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> Awaitable[None]:
        request = ASGIRequest(scope=scope, body_file=io.BytesIO())

        match request.method:
            case "PUT":
                if not any(a.match("text/plain") for a in request.accepted_types):
                    response = HttpUnsupportedContentTypeResponse(supported_types=["text/plain"])
                    return self.send_http_response(send, response=response)

                return self.stream_reservation_consumer(scope, receive, send)

            case "GET" | "POST":
                if any(a.main_type == "text" and a.sub_type == "event-stream" for a in request.accepted_types):
                    return self.event_stream_consumer(scope, receive, send)

                if not any(a.match("application/json") for a in request.accepted_types):
                    response = HttpUnsupportedContentTypeResponse(supported_types=["application/json"])
                    return self.send_http_response(send, response=response)

                return self.operation_consumer(scope, receive, send)

            case "DELETE":
                return self.operation_cancellation_consumer(scope, receive, send)

            case _:
                response = HttpMethodNotAllowedResponse(allowed_methods=["GET", "POST", "PUT", "DELETE"])
                return self.send_http_response(send, response=response)

    @staticmethod
    async def send_http_response(send: ASGISendCallable, /, *, response: HttpResponse) -> None:
        headers = {key.title(): value for key, value in response.headers.items()}
        headers_array = [(bytes(key, "ascii"), bytes(value, "latin1")) for key, value in headers.items()]

        await send(
            HTTPResponseStartEvent(
                type="http.response.start",
                status=response.status_code,
                headers=headers_array,
                trailers=False,
            ),
        )
        await send(
            HTTPResponseBodyEvent(
                type="http.response.body",
                body=response.content,
                more_body=False,
            ),
        )


# SSE (utils)


def get_stream_group_name(stream_token: str) -> str:
    return f"graphql.sse.stream.{stream_token}"


def get_all_operations_group_name(stream_token: str) -> str:
    return f"graphql.sse.ops.{stream_token}"


def get_operation_group_name(stream_token: str, operation_id: str) -> str:
    # Hash the operation ID so that it wont break group name rules
    op_hash = hashlib.md5(operation_id.encode(), usedforsecurity=False).hexdigest()
    return f"graphql.sse.op.{stream_token}.{op_hash}"


def get_sse_stream_token_key() -> str:
    return f"{undine_settings.SSE_STREAM_SESSION_PREFIX}|token"


def get_sse_stream_state_key() -> str:
    return f"{undine_settings.SSE_STREAM_SESSION_PREFIX}|state"


def get_sse_operation_key(*, operation_id: str) -> str:
    return f"{undine_settings.SSE_STREAM_SESSION_PREFIX}|operation|{operation_id}"
