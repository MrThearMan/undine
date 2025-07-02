from __future__ import annotations

from typing import TYPE_CHECKING, Any

from channels.auth import AuthMiddlewareStack
from channels.consumer import AsyncConsumer
from channels.db import aclose_old_connections
from channels.exceptions import StopConsumer
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import re_path

from undine.settings import undine_settings
from undine.utils.graphql.websocket import GraphQLOverWebSocketHandler

if TYPE_CHECKING:
    from asgiref.typing import WebSocketConnectEvent, WebSocketDisconnectEvent, WebSocketReceiveEvent
    from django.core.handlers.asgi import ASGIHandler


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


def get_websocket_enabled_app(asgi_application: ASGIHandler) -> ProtocolTypeRouter:  # pragma: no cover
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
        "http": asgi_application,
        "websocket": AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(websocket_urlpatterns))),
    })
