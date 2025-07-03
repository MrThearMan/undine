from __future__ import annotations

import asyncio
import dataclasses
import json
from functools import cached_property
from http import HTTPStatus
from typing import Any

import pytest
from asgiref.typing import ASGISendEvent
from django.contrib.auth.models import AnonymousUser, User
from graphql import GraphQLError, GraphQLFormattedError

from undine import Entrypoint, RootType, create_schema
from undine.typing import (
    CompleteMessage,
    ConnectionAckMessage,
    ConnectionInitMessage,
    ErrorMessage,
    GraphQLWebSocketCloseCode,
    NextMessage,
    PingMessage,
    PongMessage,
    ServerMessage,
    SubscribeMessage,
    WebSocketASGIScope,
)
from undine.utils.graphql.websocket import GraphQLOverWebSocketHandler, WebSocketRequest

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.django_db(transaction=True),  # For sessions
]


def default_scope(user: User | None = None) -> WebSocketASGIScope:
    return WebSocketASGIScope(
        type="websocket",
        asgi={"version": "3.0"},
        http_version="1.1",
        scheme="ws",
        server=("testserver", 80),
        client=("127.0.0.1", 0),
        root_path="",
        path="/ws/",
        raw_path=b"/ws/",
        query_string=b"",
        headers=[
            (b"host", b"testserver"),
            (b"connection", b"Upgrade"),
            (b"upgrade", b"websocket"),
            (b"sec-websocket-version", b"13"),
            (b"sec-websocket-key", b"RKr31GF3kXZqsXjVT7s3Mg=="),
            (b"sec-websocket-protocol", b"graphql-transport-ws"),
        ],
        subprotocols=["graphql-transport-ws"],
        state={},
        extensions={"websocket.http.response": {}},
        cookies={},
        path_remaining="",
        url_route={"args": (), "kwargs": {}},
        user=user or AnonymousUser(),
        session=None,  # type: ignore[typeddict-item]
    )


@dataclasses.dataclass
class MockWebSocket:
    accepted: bool = False
    messages: list[ServerMessage] = dataclasses.field(default_factory=list)
    close_code: GraphQLWebSocketCloseCode | None = None
    close_reason: str | None = None

    @cached_property
    def scope(self) -> WebSocketASGIScope:
        return default_scope()

    async def send(self, message: ASGISendEvent) -> None:
        match message["type"]:
            case "websocket.accept":
                self.accepted = True
            case "websocket.close":
                self.close_code = message["code"]  # type: ignore[assignment]
                self.close_reason = message["reason"]
            case "websocket.send":
                self.messages.append(json.loads(message["text"]))  # type: ignore[arg-type]


async def test_websocket_handler__connect__init_timeout(undine_settings) -> None:
    undine_settings.WEBSOCKET_CONNECTION_INIT_TIMEOUT_SECONDS = 0

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    await handler.connect()
    assert websocket.accepted

    assert handler.connection_init_timeout_task is not None
    await handler.connection_init_timeout_task

    assert websocket.close_code == GraphQLWebSocketCloseCode.CONNECTION_INITIALISATION_TIMEOUT
    assert websocket.close_reason == "Connection initialisation timeout"

    assert handler.connection_init_timed_out is True
    assert handler.connection_init_received is False
    assert handler.connection_acknowledged is False

    # Trying to initialize connection too late does nothing.
    message = ConnectionInitMessage(type="connection_init")
    await handler.receive(data=json.dumps(message))

    assert websocket.messages == []


async def test_websocket_handler__connect__init_completed() -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    message = ConnectionInitMessage(type="connection_init")

    assert handler.connection_init_timeout_task is None
    await handler.connect()
    assert handler.connection_init_timeout_task is not None

    await handler.receive(data=json.dumps(message))

    assert websocket.messages == [ConnectionAckMessage(type="connection_ack")]

    assert handler.connection_init_timed_out is False
    assert handler.connection_init_received is True
    assert handler.connection_acknowledged is True

    assert handler.connection_init_timeout_task.done() is False
    assert handler.connection_init_timeout_task.cancelled() is False

    with pytest.raises(asyncio.CancelledError):
        await handler.connection_init_timeout_task

    assert handler.connection_init_timeout_task.done() is True
    assert handler.connection_init_timeout_task.cancelled() is True


async def test_websocket_handler__connect__unsupported_subprotocol() -> None:
    websocket = MockWebSocket()
    websocket.scope["subprotocols"] = []
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    await handler.connect()

    assert websocket.close_code == GraphQLWebSocketCloseCode.SUBPROTOCOL_NOT_ACCEPTABLE
    assert websocket.close_reason == "Subprotocol not acceptable"


async def test_websocket_handler__connect__already_connected() -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    await handler.connect()
    await handler.connect()

    assert websocket.close_code == GraphQLWebSocketCloseCode.BAD_REQUEST
    assert websocket.close_reason == "Connection initialisation already in progress"


async def test_websocket_handler__disconnect__cancel_init_timeout() -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    await handler.connect()

    assert handler.connection_init_timeout_task is not None
    assert handler.connection_init_timeout_task.done() is False
    assert handler.connection_init_timeout_task.cancelled() is False

    await handler.disconnect()

    assert handler.connection_init_timeout_task is not None
    assert handler.connection_init_timeout_task.done() is True
    assert handler.connection_init_timeout_task.cancelled() is True


async def test_websocket_handler__disconnect__cancel_operation(undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        async def test(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    con_message = ConnectionInitMessage(type="connection_init")
    await handler.receive(data=json.dumps(con_message))

    sub_message = SubscribeMessage(type="subscribe", id="1", payload={"query": "query { test }"})
    await handler.receive(data=json.dumps(sub_message))

    operation = handler.operations.get("1")
    assert operation is not None

    assert operation.task.done() is False
    assert operation.task.cancelled() is False
    assert operation.is_completed is False

    await handler.disconnect()

    assert operation.task.done() is True
    assert operation.task.cancelled() is True
    assert operation.is_completed is True


async def test_websocket_handler__receive__no_data() -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    await handler.receive(data=None)

    assert websocket.close_code == GraphQLWebSocketCloseCode.BAD_REQUEST
    assert websocket.close_reason == "Received empty message from client"


async def test_websocket_handler__receive__not_valid_json() -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    await handler.receive(data='{"foo": "bar"')

    assert websocket.close_code == GraphQLWebSocketCloseCode.BAD_REQUEST
    assert websocket.close_reason == "WebSocket message must be a valid JSON object"


async def test_websocket_handler__receive__not_json_object() -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    await handler.receive(data='["foo", "bar"]')

    assert websocket.close_code == GraphQLWebSocketCloseCode.BAD_REQUEST
    assert websocket.close_reason == "WebSocket message must be a valid JSON object"


async def test_websocket_handler__receive__no_type_in_message() -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    await handler.receive(data='{"foo": "bar"}')

    assert websocket.close_code == GraphQLWebSocketCloseCode.BAD_REQUEST
    assert websocket.close_reason == "WebSocket message must contain a 'type' field"


async def test_websocket_handler__receive__connection_init() -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    message = ConnectionInitMessage(type="connection_init")
    await handler.receive(data=json.dumps(message))

    assert websocket.messages == [ConnectionAckMessage(type="connection_ack")]

    assert handler.connection_init_received is True
    assert handler.connection_acknowledged is True


async def test_websocket_handler__receive__connection_init__multiple_calls() -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    message = ConnectionInitMessage(type="connection_init")
    await handler.receive(data=json.dumps(message))
    await handler.receive(data=json.dumps(message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.TOO_MANY_INITIALISATION_REQUESTS
    assert websocket.close_reason == "Too many initialisation requests"


async def test_websocket_handler__receive__connection_init__payload(undine_settings) -> None:
    receive_payload: dict[str, Any] | None = None

    def connection_init_hook(request: WebSocketRequest) -> dict[str, Any] | None:
        nonlocal receive_payload
        receive_payload = request.message["payload"]
        return None

    undine_settings.WEBSOCKET_CONNECTION_INIT_HOOK = connection_init_hook

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    sent_payload = {"key": "value"}
    message = ConnectionInitMessage(type="connection_init", payload=sent_payload)
    await handler.receive(data=json.dumps(message))

    assert receive_payload == sent_payload


async def test_websocket_handler__receive__connection_init__payload__async(undine_settings) -> None:
    receive_payload: dict[str, Any] | None = None

    async def connection_init_hook(request: WebSocketRequest) -> dict[str, Any] | None:  # noqa: RUF029
        nonlocal receive_payload
        receive_payload = request.message["payload"]
        return None

    undine_settings.WEBSOCKET_CONNECTION_INIT_HOOK = connection_init_hook

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    sent_payload = {"key": "value"}
    message = ConnectionInitMessage(type="connection_init", payload=sent_payload)
    await handler.receive(data=json.dumps(message))

    assert receive_payload == sent_payload


async def test_websocket_handler__receive__connection_init__payload__graphql_error(undine_settings) -> None:
    def connection_init_hook(request: WebSocketRequest) -> dict[str, Any] | None:
        msg = "Test error"
        raise GraphQLError(msg)

    undine_settings.WEBSOCKET_CONNECTION_INIT_HOOK = connection_init_hook

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    message = ConnectionInitMessage(type="connection_init")
    await handler.receive(data=json.dumps(message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.FORBIDDEN
    assert websocket.close_reason == "Test error"

    assert handler.connection_init_received is True
    assert handler.connection_acknowledged is False


async def test_websocket_handler__receive__connection_init__payload__graphql_error__async(undine_settings) -> None:
    async def connection_init_hook(request: WebSocketRequest) -> dict[str, Any] | None:  # noqa: RUF029
        msg = "Test error"
        raise GraphQLError(msg)

    undine_settings.WEBSOCKET_CONNECTION_INIT_HOOK = connection_init_hook

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    message = ConnectionInitMessage(type="connection_init")
    await handler.receive(data=json.dumps(message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.FORBIDDEN
    assert websocket.close_reason == "Test error"

    assert handler.connection_init_received is True
    assert handler.connection_acknowledged is False


async def test_websocket_handler__receive__connection_init__payload__generic_error(undine_settings) -> None:
    def connection_init_hook(request: WebSocketRequest) -> dict[str, Any] | None:
        msg = "Test error"
        raise ValueError(msg)

    undine_settings.WEBSOCKET_CONNECTION_INIT_HOOK = connection_init_hook

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    message = ConnectionInitMessage(type="connection_init")
    await handler.receive(data=json.dumps(message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.FORBIDDEN
    assert websocket.close_reason == "Forbidden"

    assert handler.connection_init_received is True
    assert handler.connection_acknowledged is False


async def test_websocket_handler__receive__connection_init__payload__generic_error__async(undine_settings) -> None:
    async def connection_init_hook(request: WebSocketRequest) -> dict[str, Any] | None:  # noqa: RUF029
        msg = "Test error"
        raise ValueError(msg)

    undine_settings.WEBSOCKET_CONNECTION_INIT_HOOK = connection_init_hook

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    message = ConnectionInitMessage(type="connection_init")
    await handler.receive(data=json.dumps(message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.FORBIDDEN
    assert websocket.close_reason == "Forbidden"

    assert handler.connection_init_received is True
    assert handler.connection_acknowledged is False


async def test_websocket_handler__receive__connection_init__payload__in_response(undine_settings) -> None:
    def connection_init_hook(request: WebSocketRequest) -> dict[str, Any] | None:
        return request.message["payload"]

    undine_settings.WEBSOCKET_CONNECTION_INIT_HOOK = connection_init_hook

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    sent_payload = {"key": "value"}
    message = ConnectionInitMessage(type="connection_init", payload=sent_payload)
    await handler.receive(data=json.dumps(message))

    assert websocket.messages == [ConnectionAckMessage(type="connection_ack", payload=sent_payload)]


async def test_websocket_handler__receive__connection_init__payload__invalid(undine_settings) -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    message = ConnectionInitMessage(type="connection_init", payload=1)  # type: ignore[typeddict-item]
    await handler.receive(data=json.dumps(message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.BAD_REQUEST
    assert websocket.close_reason == "ConnectionInit 'payload' must be a valid JSON object"


async def test_websocket_handler__receive__ping() -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    message = PingMessage(type="ping")
    await handler.receive(data=json.dumps(message))

    assert websocket.messages == [PongMessage(type="pong")]


async def test_websocket_handler__receive__ping__payload(undine_settings) -> None:
    receive_payload: dict[str, Any] | None = None

    def ping_hook(request: WebSocketRequest) -> dict[str, Any] | None:
        nonlocal receive_payload
        receive_payload = request.message["payload"]
        return None

    undine_settings.WEBSOCKET_PING_HOOK = ping_hook

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    sent_payload = {"key": "value"}
    message = PingMessage(type="ping", payload=sent_payload)
    await handler.receive(data=json.dumps(message))

    assert sent_payload == receive_payload


async def test_websocket_handler__receive__ping__payload__async(undine_settings) -> None:
    receive_payload: dict[str, Any] | None = None

    async def ping_hook(request: WebSocketRequest) -> dict[str, Any] | None:  # noqa: RUF029
        nonlocal receive_payload
        receive_payload = request.message["payload"]
        return None

    undine_settings.WEBSOCKET_PING_HOOK = ping_hook

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    sent_payload = {"key": "value"}
    message = PingMessage(type="ping", payload=sent_payload)
    await handler.receive(data=json.dumps(message))

    assert sent_payload == receive_payload


async def test_websocket_handler__receive__ping__payload__in_response(undine_settings) -> None:
    def ping_hook(request: WebSocketRequest) -> dict[str, Any] | None:
        return request.message["payload"]

    undine_settings.WEBSOCKET_PING_HOOK = ping_hook

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    sent_payload = {"key": "value"}
    message = PingMessage(type="ping", payload=sent_payload)
    await handler.receive(data=json.dumps(message))

    assert websocket.messages == [PongMessage(type="pong", payload=sent_payload)]


async def test_websocket_handler__receive__ping__payload__invalid(undine_settings) -> None:
    def ping_hook(request: WebSocketRequest) -> dict[str, Any] | None:
        return request.message["payload"]

    undine_settings.WEBSOCKET_PING_HOOK = ping_hook

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    message = PingMessage(type="ping", payload=1)  # type: ignore[typeddict-item]
    await handler.receive(data=json.dumps(message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.BAD_REQUEST
    assert websocket.close_reason == "Ping 'payload' must be a valid JSON object"


async def test_websocket_handler__receive__pong() -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    message = PongMessage(type="pong")
    await handler.receive(data=json.dumps(message))

    # Pong does nothing by default
    assert websocket.messages == []
    assert websocket.close_code is None
    assert websocket.close_reason is None


async def test_websocket_handler__receive__pong__payload(undine_settings) -> None:
    receive_payload: dict[str, Any] | None = None

    def pong_hook(request: WebSocketRequest) -> dict[str, Any] | None:
        nonlocal receive_payload
        receive_payload = request.message["payload"]
        return None

    undine_settings.WEBSOCKET_PONG_HOOK = pong_hook

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    sent_payload = {"key": "value"}
    message = PongMessage(type="pong", payload=sent_payload)
    await handler.receive(data=json.dumps(message))

    assert receive_payload == sent_payload


async def test_websocket_handler__receive__pong__payload__async(undine_settings) -> None:
    receive_payload: dict[str, Any] | None = None

    async def pong_hook(request: WebSocketRequest) -> dict[str, Any] | None:  # noqa: RUF029
        nonlocal receive_payload
        receive_payload = request.message["payload"]
        return None

    undine_settings.WEBSOCKET_PONG_HOOK = pong_hook

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    sent_payload = {"key": "value"}
    message = PongMessage(type="pong", payload=sent_payload)
    await handler.receive(data=json.dumps(message))

    assert receive_payload == sent_payload


async def test_websocket_handler__receive__pong__invalid() -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    message = PongMessage(type="pong", payload=1)  # type: ignore[typeddict-item]
    await handler.receive(data=json.dumps(message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.BAD_REQUEST
    assert websocket.close_reason == "Pong 'payload' must be a valid JSON object"


async def test_websocket_handler__receive__subscribe(undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        async def test(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    handler.connection_acknowledged = True

    message = SubscribeMessage(type="subscribe", id="1", payload={"query": "query { test }"})
    await handler.receive(data=json.dumps(message))

    operation = handler.operations.get("1")
    assert operation is not None

    assert operation.task.done() is False
    assert operation.task.cancelled() is False
    assert operation.is_completed is False

    await operation.task

    assert websocket.messages == [
        NextMessage(type="next", id="1", payload={"data": {"test": "Hello, World!"}}),
        CompleteMessage(type="complete", id="1"),
    ]

    assert operation.task.done() is True
    assert operation.task.cancelled() is False
    assert operation.is_completed is True


async def test_websocket_handler__receive__subscribe__unauthorized(undine_settings) -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    message = SubscribeMessage(type="subscribe", id="1", payload={"query": "query { test }"})
    await handler.receive(data=json.dumps(message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.UNAUTHORIZED
    assert websocket.close_reason == "Unauthorized"


async def test_websocket_handler__receive__subscribe__duplicate_operation(undine_settings) -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    handler.connection_acknowledged = True

    message = SubscribeMessage(type="subscribe", id="1", payload={"query": "query { test }"})

    await handler.receive(data=json.dumps(message))

    operation = handler.operations.get("1")
    assert operation is not None

    assert operation.task.done() is False
    assert operation.task.cancelled() is False
    assert operation.is_completed is False

    await handler.receive(data=json.dumps(message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.SUBSCRIBER_ALREADY_EXISTS
    assert websocket.close_reason == "Subscriber for 1 already exists"

    assert operation.task.done() is True
    assert operation.task.cancelled() is True
    assert operation.is_completed is True


async def test_websocket_handler__receive__subscribe__payload__parsing_error(undine_settings) -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    handler.connection_acknowledged = True

    message = SubscribeMessage(type="subscribe", id="1", payload={"foo": "bar"})

    await handler.receive(data=json.dumps(message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.BAD_REQUEST
    assert websocket.close_reason == (
        "Request data must contain either a `query` string describing the graphql document "
        "or a `documentId` string identifying a persisted document."
    )


async def test_websocket_handler__receive__subscribe__error(undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        async def test(self) -> str:
            msg = "Test error"
            raise GraphQLError(msg)

    undine_settings.SCHEMA = create_schema(query=Query)

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    handler.connection_acknowledged = True

    message = SubscribeMessage(type="subscribe", id="1", payload={"query": "query { test }"})
    await handler.receive(data=json.dumps(message))

    operation = handler.operations.get("1")
    assert operation is not None

    assert operation.task.done() is False
    assert operation.task.cancelled() is False
    assert operation.is_completed is False

    await operation.task

    assert websocket.messages == [
        ErrorMessage(
            type="error",
            id="1",
            payload=[
                GraphQLFormattedError(
                    message="Test error",
                    path=["test"],
                    extensions={"status_code": HTTPStatus.BAD_REQUEST},
                ),
            ],
        ),
    ]

    assert operation.task.done() is True
    assert operation.task.cancelled() is False
    assert operation.is_completed is True


async def test_websocket_handler__receive__subscribe__already_completed(undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        async def test(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    handler.connection_acknowledged = True

    message = SubscribeMessage(type="subscribe", id="1", payload={"query": "query { test }"})
    await handler.receive(data=json.dumps(message))

    operation = handler.operations.get("1")
    assert operation is not None

    assert operation.task.done() is False
    assert operation.task.cancelled() is False

    assert operation.is_completed is False
    operation.set_completed()
    assert operation.is_completed is True

    await operation.task

    assert websocket.messages == []

    assert operation.task.done() is True
    assert operation.task.cancelled() is False
    assert operation.is_completed is True


async def test_websocket_handler__receive__subscribe__already_completed__error(undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        async def test(self) -> str:
            msg = "Test error"
            raise GraphQLError(msg)

    undine_settings.SCHEMA = create_schema(query=Query)

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    handler.connection_acknowledged = True

    message = SubscribeMessage(type="subscribe", id="1", payload={"query": "query { test }"})
    await handler.receive(data=json.dumps(message))

    operation = handler.operations.get("1")
    assert operation is not None

    assert operation.task.done() is False
    assert operation.task.cancelled() is False

    assert operation.is_completed is False
    operation.set_completed()
    assert operation.is_completed is True

    await operation.task

    assert websocket.messages == []

    assert operation.task.done() is True
    assert operation.task.cancelled() is False
    assert operation.is_completed is True


async def test_websocket_handler__receive__subscribe__operation_id_missing(undine_settings) -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    handler.connection_acknowledged = True

    message = SubscribeMessage(type="subscribe", payload={"query": "query { test }"})  # type: ignore[typeddict-item]
    await handler.receive(data=json.dumps(message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.BAD_REQUEST
    assert websocket.close_reason == "Subscribe message must contain an 'id' field"


async def test_websocket_handler__receive__subscribe__operation_id_not_string(undine_settings) -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    handler.connection_acknowledged = True

    message = SubscribeMessage(type="subscribe", id=1, payload={"query": "query { test }"})  # type: ignore[typeddict-item]
    await handler.receive(data=json.dumps(message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.BAD_REQUEST
    assert websocket.close_reason == "Subscription 'id' must be a string"


async def test_websocket_handler__receive__subscribe__payload_missing(undine_settings) -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    handler.connection_acknowledged = True

    message = SubscribeMessage(type="subscribe", id="1")  # type: ignore[typeddict-item]
    await handler.receive(data=json.dumps(message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.BAD_REQUEST
    assert websocket.close_reason == "Subscribe message must contain an 'payload' field"


async def test_websocket_handler__receive__subscribe__payload_not_dict(undine_settings) -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    handler.connection_acknowledged = True

    message = SubscribeMessage(type="subscribe", id="1", payload=1)  # type: ignore[typeddict-item]
    await handler.receive(data=json.dumps(message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.BAD_REQUEST
    assert websocket.close_reason == "Subscription 'payload' must be a valid JSON object"


async def test_websocket_handler__receive__complete(undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        async def test(self) -> str:
            msg = "Test error"
            raise GraphQLError(msg)

    undine_settings.SCHEMA = create_schema(query=Query)

    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    handler.connection_acknowledged = True

    message = SubscribeMessage(type="subscribe", id="1", payload={"query": "query { test }"})
    await handler.receive(data=json.dumps(message))

    operation = handler.operations.get("1")
    assert operation is not None

    assert operation.task.done() is False
    assert operation.task.cancelled() is False
    assert operation.is_completed is False

    complete_message = CompleteMessage(type="complete", id="1")
    await handler.receive(data=json.dumps(complete_message))

    assert operation.task.done() is True
    assert operation.task.cancelled() is True
    assert operation.is_completed is True

    with pytest.raises(asyncio.CancelledError):
        await operation.task

    assert websocket.messages == []

    assert operation.task.done() is True
    assert operation.task.cancelled() is True
    assert operation.is_completed is True


async def test_websocket_handler__receive__complete__operation_not_found(undine_settings) -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    complete_message = CompleteMessage(type="complete", id="1")
    await handler.receive(data=json.dumps(complete_message))

    assert websocket.messages == []


async def test_websocket_handler__receive__complete__operation_id_missing(undine_settings) -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    complete_message = CompleteMessage(type="complete")  # type: ignore[typeddict-item]
    await handler.receive(data=json.dumps(complete_message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.BAD_REQUEST
    assert websocket.close_reason == "Complete message must contain an 'id' field"


async def test_websocket_handler__receive__complete__operation_id_not_string(undine_settings) -> None:
    websocket = MockWebSocket()
    handler = GraphQLOverWebSocketHandler(websocket=websocket)

    complete_message = CompleteMessage(type="complete", id=1)  # type: ignore[typeddict-item]
    await handler.receive(data=json.dumps(complete_message))

    assert websocket.close_code == GraphQLWebSocketCloseCode.BAD_REQUEST
    assert websocket.close_reason == "Complete message 'id' must be a string"
