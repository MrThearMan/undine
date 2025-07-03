from __future__ import annotations

import asyncio
import dataclasses
import json
import uuid
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Self

from asgiref.typing import WebSocketConnectEvent, WebSocketReceiveEvent
from channels.auth import AuthMiddlewareStack

from undine.exceptions import WebSocketConnectionClosedError
from undine.integrations.channels import GraphQLWebSocketConsumer
from undine.settings import undine_settings
from undine.typing import CompleteMessage, ConnectionInitMessage, SubscribeMessage

if TYPE_CHECKING:
    from asgiref.typing import ASGISendEvent, WebSocketCloseEvent, WebSocketDisconnectEvent

    from undine.typing import (
        ClientMessage,
        ConnectionAckMessage,
        ErrorMessage,
        NextMessage,
        ServerMessage,
        WebSocketASGIScope,
    )


__all__ = [
    "TestWebSocket",
]


@dataclasses.dataclass(slots=True, kw_only=True)
class TestWebSocket:
    """A testing utility for sending and receiving messages from the given consumer."""

    scope: WebSocketASGIScope
    """ASGI scope for the WebSocket request."""

    consumer: GraphQLWebSocketConsumer = dataclasses.field(default_factory=GraphQLWebSocketConsumer)
    """Consumer for the WebSocket."""

    task: asyncio.Task | None = None
    """Consumer task with AuthMiddlewareStack applied. Added on context enter."""

    messages: asyncio.Queue[ClientMessage] = dataclasses.field(default_factory=asyncio.Queue)
    """Messages placed here are picked up by the consumer."""

    responses: asyncio.Queue[ServerMessage | None] = dataclasses.field(default_factory=asyncio.Queue)
    """Messages from the consumer are placed here."""

    accepted: asyncio.Event = dataclasses.field(default_factory=asyncio.Event)
    """Set if the connection is accepted after 'ConnectionInit' message is sent."""

    close_event: WebSocketCloseEvent | None = None
    """Set if the connection is closed."""

    async def connection_init(
        self,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float | None = 3,
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
        timeout: float | None = 3,
    ) -> NextMessage | ErrorMessage:
        """
        Create a subscription for the given payload.

        If Next message is received, should wait for subsequent messages until receiving a Complete message.
        If Error message is received (at any point), no more messages will be sent.

        :param payload: The subscription payload.
        :param operation_id: The ID of the subscription operation.
        :param timeout: Timeout in seconds for receiving the first response.
        """
        operation_id = operation_id or str(uuid.uuid4())
        message = SubscribeMessage(type="subscribe", id=operation_id, payload=payload)
        return await self.send_and_receive(message=message, timeout=timeout)  # type: ignore[return-value]

    async def unsubscribe(self, *, operation_id: str) -> None:
        """
        Unsubscribes from a subscription early.

        Requires that some part of the subscription delays execution with
        some form of `loop.call_later`, (e.g. `asyncio.sleep` with a positive delay).
        Does not guarantee how many subscription messages will still be sent.
        Should manually fetch the operation from `consumer.handler.operations` and
        await its `.task` to complete with a `asyncio.CancelledError`.

        :param operation_id: The ID of the subscription operation.
        """
        message = CompleteMessage(type="complete", id=operation_id)
        await self.send(message=message)

    async def send_and_receive(self, message: ClientMessage, *, timeout: float | None = 3) -> ServerMessage:
        """
        Send a message to the server and wait for the response.

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

        :param message: The message to send.
        :raises WebSocketConnectionClosedError: Connection is closed.
        """
        if self.close_event is not None:
            raise WebSocketConnectionClosedError(reason=self.close_event["reason"], code=self.close_event["code"])

        await self.messages.put(message)

    async def receive(self, *, timeout: float | None = 3) -> ServerMessage:
        """
        Receive a message from the server.

        :param timeout: Timeout for receiving the message.
        :raises WebSocketConnectionClosedError: Connection is closed.
        :raises TimeoutError: Timeout reached.
        """
        if self.close_event is not None:
            raise WebSocketConnectionClosedError(reason=self.close_event["reason"], code=self.close_event["code"])

        timeout = None if undine_settings.TESTING_CLIENT_NO_ASYNC_TIMEOUT else timeout

        try:
            data = await asyncio.wait_for(self.responses.get(), timeout)
        except TimeoutError as error:
            msg = "Timeout waiting for message from server."
            raise TimeoutError(msg) from error

        if self.close_event is not None:
            raise WebSocketConnectionClosedError(reason=self.close_event["reason"], code=self.close_event["code"])

        if data is None:
            raise WebSocketConnectionClosedError

        return data

    async def __aenter__(self) -> Self:
        """Start the WebSocket connection."""
        self.accepted.clear()
        self.close_event = None

        stack = AuthMiddlewareStack(self.consumer)
        self.task = asyncio.create_task(stack(self.scope, self._to_consumer, self._from_consumer))

        await self.accepted.wait()
        return self

    async def __aexit__(self, *args: object) -> None:
        """Terminate the WebSocket connection."""
        # Cancel pending tasks in the consumer
        await self.consumer.handler.disconnect()

        # Shouldn't happen, but just in case.
        if self.task is None:  # pragma: no cover
            return

        # Make sure the task is done.
        if not self.task.done():
            self.task.cancel()

        timeout = None if undine_settings.TESTING_CLIENT_NO_ASYNC_TIMEOUT else 3

        with suppress(BaseException):
            # IDK why, but we need to wrap the task with `asyncio.wait` or we might wait here forever...
            await asyncio.wait(self.task, timeout=timeout)

    async def _to_consumer(self) -> WebSocketConnectEvent | WebSocketReceiveEvent | WebSocketDisconnectEvent:
        """
        Send an event to the consumer. Called automatically by `self.task`.
        Will wait for new messages until the connection is closed, or specified timeout is reached.

        :returns: The event to send to the consumer.
        :raises WebSocketConnectionClosedError: Connection is closed.
        :raises TimeoutError: Timeout reached.
        """
        if not self.accepted.is_set():
            return WebSocketConnectEvent(type="websocket.connect")

        if self.close_event is not None:
            raise WebSocketConnectionClosedError(reason=self.close_event["reason"], code=self.close_event["code"])

        timeout = None if undine_settings.TESTING_CLIENT_NO_ASYNC_TIMEOUT else 3

        try:
            message = await asyncio.wait_for(self.messages.get(), timeout=timeout)
        except TimeoutError as error:
            msg = "Timeout waiting for message from client."
            raise TimeoutError(msg) from error

        return WebSocketReceiveEvent(type="websocket.receive", text=json.dumps(message), bytes=None)

    async def _from_consumer(self, event: ASGISendEvent) -> None:
        """
        Event received from the consumer. Called automatically by `self.task`.

        :param event: The event received from the consumer.
        :raises RuntimeError: Unexpected event.
        """
        match event["type"]:
            case "websocket.accept":
                self.accepted.set()

            case "websocket.close":
                # Set 'None' to prevent receive from timing out.
                await self.responses.put(None)
                self.close_event = event

            case "websocket.send" if event["text"] is not None:
                await self.responses.put(json.loads(event["text"]))

            case _:
                # Set 'None' to prevent receive from timing out.
                await self.responses.put(None)
                msg = f"Unexpected event: {json.dumps(event)}"
                raise RuntimeError(msg)
