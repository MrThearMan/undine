from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any

from channels.auth import AuthMiddlewareStack
from channels.consumer import AsyncConsumer
from channels.db import aclose_old_connections
from channels.exceptions import StopConsumer
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.handlers.asgi import ASGIRequest
from django.urls import re_path

from undine.http.utils import get_graphql_event_stream_token
from undine.settings import undine_settings
from undine.utils.graphql.websocket import GraphQLOverWebSocketHandler

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from asgiref.typing import (
        ASGI3Application,
        ASGIReceiveCallable,
        ASGISendCallable,
        WebSocketConnectEvent,
        WebSocketDisconnectEvent,
        WebSocketReceiveEvent,
    )
    from django.core.handlers.asgi import ASGIHandler

    from undine.typing import HTTPASGIScope

__all__ = [
    "GraphQLWebSocketConsumer",
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


class GraphQLSSESingleConnectionConsumer(AsyncConsumer):  # TODO: Implement
    """Single connection mode consumer for GraphQL over Server-Sent Events."""


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
