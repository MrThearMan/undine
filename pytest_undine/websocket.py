from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Self

from asgiref.typing import WebSocketConnectEvent, WebSocketReceiveEvent
from channels.auth import AuthMiddlewareStack

from undine.integrations.channels import GraphQLWebSocketConsumer
from undine.typing import ConnectionInitMessage, SubscribeMessage

if TYPE_CHECKING:
    from asgiref.typing import ASGISendEvent, WebSocketDisconnectEvent

    from undine.typing import (
        ClientMessage,
        ConnectionAckMessage,
        ErrorMessage,
        NextMessage,
        ServerMessage,
        WebSocketASGIScope,
    )

    from .client import GraphQLClient


__all__ = [
    "WebSocketConnectionClosedError",
    "WebSocketContextManager",
]


class WebSocketConnectionClosedError(Exception):
    """Raised when a test client WebSocket is closed."""

    def __init__(self, msg: str = "") -> None:
        msg = msg or "Websocket connection closed"
        super().__init__(msg)


class WebSocketContextManager:
    """A context manager for testing WebSockets to the GraphQL schema."""

    def __init__(self, client: GraphQLClient, scope: WebSocketASGIScope) -> None:
        self.client = client
        self.scope = scope

        self.timeout: float = 10
        """Timeout in seconds for receiving new messages to send."""

        self.consumer = GraphQLWebSocketConsumer()
        self.execute = AuthMiddlewareStack(self.consumer)
        self.task: asyncio.Task | None = None

        self.messages: asyncio.Queue[str] = asyncio.Queue()
        self.responses: asyncio.Queue[str | None] = asyncio.Queue()

        self.accepted = asyncio.Event()
        self.closed = asyncio.Event()

    async def connection_init(
        self,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float = 3,
    ) -> ConnectionAckMessage:
        """
        Send a ConnectionInit message to the server.
        This is required before sending any other messages.

        :param payload: The connection init payload.
        :param timeout: Timeout in seconds for receiving the response.
        """
        message = ConnectionInitMessage(type="connection_init")
        if payload is not None:
            message["payload"] = payload
        return await self.send_and_receive(message=message, timeout=timeout)  # type: ignore[return-value]

    async def subscribe(
        self,
        payload: dict[str, Any],
        *,
        operation_id: str | None = None,
        timeout: float = 3,
    ) -> NextMessage | ErrorMessage:
        """
        Send a Subscribe message to the server.
        If Next message is received, should wait for subsequent messages until receiving a Complete message.
        If Error message is received, no more messages will be sent.

        :param payload: The subscription payload.
        :param operation_id: The ID of the subscription operation.
        :param timeout: Timeout in seconds for receiving the first response.
        """
        operation_id = operation_id or str(uuid.uuid4())
        message = SubscribeMessage(type="subscribe", id=operation_id, payload=payload)
        return await self.send_and_receive(message=message, timeout=timeout)  # type: ignore[return-value]

    async def send_and_receive(self, message: ClientMessage, *, timeout: float = 3) -> ServerMessage:
        """
        Send a message to the server and wait for the response.
        Note that this manager can only send a single message at a time.

        :param message: The message to send.
        :param timeout: Timeout in seconds for receiving the response.
        :raises WebSocketConnectionClosedError: Connection is closed.
        :raises TimeoutError: Timeout reached.
        """
        await self.send(message=message)
        return await self.receive(timeout=timeout)

    async def send(self, message: ClientMessage) -> None:
        """
        Send a message to the server.
        Note that this manager can only send a single message at a time.

        :param message: The message to send.
        :raises WebSocketConnectionClosedError: Connection is closed.
        """
        if self.closed.is_set():
            raise WebSocketConnectionClosedError
        await self.messages.put(json.dumps(message))

    async def receive(self, *, timeout: float = 3) -> ServerMessage:
        """
        Receive the next message from the server.

        :param timeout: Timeout for receiving the message.
        :raises WebSocketConnectionClosedError: Connection is closed.
        :raises TimeoutError: Timeout reached.
        """
        if self.closed.is_set():
            raise WebSocketConnectionClosedError

        try:
            data = await asyncio.wait_for(self.responses.get(), timeout)
        except TimeoutError as error:
            msg = "Timeout waiting for message from server."
            raise TimeoutError(msg) from error

        if data is None:
            raise WebSocketConnectionClosedError

        return json.loads(data)

    async def __aenter__(self) -> Self:
        """Start the WebSocket connection."""
        self.task = asyncio.create_task(self.execute(self.scope, self._to_consumer, self._from_consumer))
        await self.accepted.wait()
        return self

    async def __aexit__(self, *args: object) -> None:
        """Terminate the WebSocket connection."""
        self.accepted.clear()
        self.closed.clear()

        # Shouldn't happen, but just in case.
        if self.task is None:  # pragma: no cover
            return

        # Cancel pending tasks in the consumer
        await self.consumer.handler.disconnect()

        # Make sure the task is done.
        if not self.task.done():
            self.task.cancel()
        with suppress(BaseException):
            await self.task

    async def _to_consumer(self) -> WebSocketConnectEvent | WebSocketReceiveEvent | WebSocketDisconnectEvent:
        """
        Send an event to the consumer.
        Will wait for new messages until the connection is closed, or specified timeout is reached.

        :returns: The event to send to the consumer.
        :raises WebSocketConnectionClosedError: Connection is closed.
        :raises TimeoutError: Timeout reached.
        """
        if not self.accepted.is_set():
            return WebSocketConnectEvent(type="websocket.connect")

        if self.closed.is_set():
            raise WebSocketConnectionClosedError

        try:
            message = await asyncio.wait_for(self.messages.get(), timeout=self.timeout)
        except TimeoutError as error:
            msg = "Timeout waiting for message from client."
            raise TimeoutError(msg) from error

        return WebSocketReceiveEvent(type="websocket.receive", text=message, bytes=None)

    async def _from_consumer(self, event: ASGISendEvent) -> None:
        """
        Event received from the consumer.

        :param event: The event received from the consumer.
        :raises RuntimeError: Unexpected event.
        """
        match event["type"]:
            case "websocket.accept":
                self.accepted.set()

            case "websocket.close":
                # Set 'None' to prevent receive from timing out.
                await self.responses.put(None)
                self.closed.set()

            case "websocket.send" if event["text"] is not None:
                await self.responses.put(event["text"])

            case _:
                # Set 'None' to prevent receive from timing out.
                await self.responses.put(None)
                msg = f"Unexpected event: {json.dumps(event)}"
                raise RuntimeError(msg)
