from __future__ import annotations

import asyncio
import io
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Never

from channels.auth import AuthMiddlewareStack
from channels.consumer import AsyncConsumer
from channels.db import aclose_old_connections
from channels.exceptions import StopConsumer
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.handlers.asgi import ASGIRequest
from django.urls import re_path

from undine.dataclasses import CompletedEventSC
from undine.exceptions import ContinueConsumer
from undine.http.utils import get_graphql_event_stream_token
from undine.settings import undine_settings
from undine.typing import SSEOperationCancelEvent, SSEOperationResultEvent
from undine.utils.graphql.server_sent_events import (
    GraphQLOverSSESingleConnectionHandler,
    SSERequest,
    execute_graphql_sse_sc,
)
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
    from django.core.handlers.asgi import ASGIHandler

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol, HTTPASGIScope

__all__ = [
    "GraphQLSSESingleConnectionConsumer",
    "GraphQLWebSocketConsumer",
    "get_sse_enabled_app",
    "get_websocket_and_sse_enabled_app",
    "get_websocket_enabled_app",
]


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


# TODO: Maybe split this into separate consumers for each method? Simpler?
class GraphQLSSESingleConnectionConsumer(AsyncConsumer):
    """Single connection mode consumer for GraphQL over Server-Sent Events."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.handler = GraphQLOverSSESingleConnectionHandler(sse=self)
        self.messages: list[HTTPRequestEvent] = []

        # Request is always set in `http_request` before any other method is called.
        self.request: DjangoRequestProtocol = None  # type: ignore[assignment]

        # Set by the stream consumer.
        self.stream_group_name: str = ""

        # Set by operation consumers.
        self.operation: asyncio.Task | None = None

    # HTTP interface

    async def http_request(self, message: HTTPRequestEvent) -> None:
        self.messages.append(message)

        if not message.get("more_body"):
            self.request = SSERequest(scope=self.scope, messages=self.messages)  # type: ignore[assignment]

            try:
                await self.handler.receive(request=self.request)
            except ContinueConsumer:
                return

            await self.disconnect()
            raise StopConsumer

    async def http_disconnect(self, message: HTTPDisconnectEvent) -> Never:
        # TODO: Any channel consumer may receive this event.
        #  This can be either the consumer handling the event stream
        #  or any consumer handling an ongoing operation.
        # TODO: When subscription ends, client sends a 'disconnect' message.
        #  but the event stream should still be open.
        await self.disconnect()
        await aclose_old_connections()
        raise StopConsumer

    async def disconnect(self) -> None:
        if self.operation is not None:
            self.operation.cancel()
            with suppress(BaseException):
                await self.operation

        if self.stream_group_name:
            await self.channel_layer.group_discard(group=self.stream_group_name, channel=self.channel_name)
            await self.handler.stop_event_stream(request=self.request)

    # SSE interface

    async def start_stream(self, stream_token: str) -> None:
        self.stream_group_name = get_stream_group_name(stream_token=stream_token)
        await self.channel_layer.group_add(group=self.stream_group_name, channel=self.channel_name)

    async def run_operation(self, stream_token: str, operation_id: str, params: GraphQLHttpParams) -> None:
        stream_group_name = get_stream_group_name(stream_token=stream_token)
        operation_group_name = get_operation_group_name(stream_token=stream_token, operation_id=operation_id)
        message_type = self.sse_operation_event.__name__.replace("_", ".")

        await self.channel_layer.group_add(group=operation_group_name, channel=self.channel_name)

        async def execute() -> None:
            completed: bool = False
            try:
                async for event in execute_graphql_sse_sc(operation_id, params, self.request):
                    completed = completed or event.event == "complete"
                    await self.channel_layer.group_send(
                        group=stream_group_name,
                        message=SSEOperationResultEvent(type=message_type, event=event.encode()),
                    )

            except asyncio.CancelledError:
                # Make sure completed event is sent even if the subscription is cancelled.
                if not completed:
                    event = CompletedEventSC(operation_id=operation_id)
                    await self.channel_layer.group_send(
                        group=stream_group_name,
                        message=SSEOperationResultEvent(type=message_type, event=event.encode()),
                    )

        try:
            self.operation = asyncio.create_task(execute())
            await self.operation
        finally:
            await self.channel_layer.group_discard(group=operation_group_name, channel=self.channel_name)

    async def cancel_operation(self, stream_token: str, operation_id: str) -> None:
        operation_group_name = get_operation_group_name(stream_token=stream_token, operation_id=operation_id)
        message_type = self.sse_operation_cancel.__name__.replace("_", ".")
        event = SSEOperationCancelEvent(type=message_type)
        # TODO: Doesn't work since we would need to get back to the consumer loop
        #  for the group message to be processed.
        await self.channel_layer.group_send(group=operation_group_name, message=event)

    # Consumer group methods

    async def sse_operation_event(self, event: SSEOperationResultEvent) -> None:
        """Called in the stream consumer to send an event to the client."""
        await self.handler.send_body(body=event["event"], more_body=True)

    async def sse_operation_cancel(self, event: SSEOperationCancelEvent) -> None:
        """Called in an operation consumer to cancel its operation."""
        if self.operation is not None:
            self.operation.cancel()


def get_stream_group_name(*, stream_token: str) -> str:
    return f"graphql.sse.{stream_token}"


def get_operation_group_name(*, stream_token: str, operation_id: str) -> str:
    return f"graphql.sse.{stream_token}.{operation_id}"


class GraphQLSSERouter:  # TODO: test
    """
    Router that sends GraphQL over Server-Sent Events requests
    to the single connection mode handler when required.
    """

    def __init__(self, asgi_application: ASGI3Application, sse_application: ASGI3Application) -> None:
        self.asgi_application = asgi_application
        self.sse_application = sse_application

    def __call__(self, scope: HTTPASGIScope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> Awaitable[None]:
        path = scope["path"].removeprefix("/").removesuffix("/")
        graphql_path = undine_settings.GRAPHQL_PATH.removeprefix("/").removesuffix("/")

        # Only the GraphQL endpoint can have GraphQL over SSE requests.
        if path != graphql_path:
            return self.asgi_application(scope, receive, send)

        # If distinct connections mode can be used, use it.
        http_version = tuple(int(part) for part in str(float(scope["http_version"])).split("."))
        if http_version >= (2, 0) or undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1:
            return self.asgi_application(scope, receive, send)

        # Otherwise, if this request is one of the GraphQL over SSE requests,
        # single connection mode is required and needs to be routed to the SSE application.
        request = ASGIRequest(scope=scope, body_file=io.BytesIO())
        if request.method in {"PUT", "DELETE"} or (
            request.method in {"GET", "POST"} and get_graphql_event_stream_token(request)
        ):
            return self.sse_application(scope, receive, send)

        return self.asgi_application(scope, receive, send)


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
    sse_urlpatterns = [re_path(undine_settings.GRAPHQL_PATH, GraphQLSSESingleConnectionConsumer.as_asgi())]
    sse_application = AuthMiddlewareStack(URLRouter(sse_urlpatterns))

    return GraphQLSSERouter(asgi_application=django_application, sse_application=sse_application)


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
