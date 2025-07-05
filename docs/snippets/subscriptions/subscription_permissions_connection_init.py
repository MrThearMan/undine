from typing import Any

from undine.exceptions import GraphQLPermissionError
from undine.utils.graphql.websocket import WebSocketRequest


def connection_init_hook(request: WebSocketRequest) -> dict[str, Any] | None:
    if not request.user.is_superuser:
        msg = "Only superusers can establish a connection"
        raise GraphQLPermissionError(msg)
