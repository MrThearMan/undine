from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from channels.auth import AuthMiddlewareStack
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import re_path

from undine.settings import undine_settings
from undine.utils.graphql.websocket import GraphQLOverWebSocketHandler

if TYPE_CHECKING:
    from django.core.handlers.asgi import ASGIHandler

    from undine.typing import GraphQLWebSocketCloseCode, ServerMessage


__all__ = [
    "GraphQLWebSocketConsumer",
    "get_websocket_enabled_app",
]


class GraphQLWebSocketConsumer(AsyncWebsocketConsumer):
    """Channels consumer receiving messages from the WebSocket for the GraphQL over WebSocket Protocol."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.handler = GraphQLOverWebSocketHandler(websocket=self)

    async def connect(self) -> None:
        await self.handler.connect()

    async def disconnect(self, close_code: GraphQLWebSocketCloseCode) -> None:
        await self.handler.disconnect()

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        await self.handler.receive(data=text_data)

    async def send_message(self, message: ServerMessage) -> None:
        text_data = json.dumps(message, separators=(",", ":"))
        await self.send(text_data=text_data)


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
