from __future__ import annotations

import asyncio
import datetime
import json
import uuid
from contextlib import suppress
from functools import partial
from http import HTTPStatus
from typing import AsyncIterator, Literal
from unittest.mock import patch
from urllib.parse import urlsplit

import freezegun
import pytest
from asgiref.typing import (
    ASGIReceiveEvent,
    ASGIVersions,
    HTTPRequestEvent,
    HTTPResponseBodyEvent,
    HTTPResponseStartEvent,
    HTTPScope,
)
from channels.auth import AuthMiddlewareStack
from django.http import HttpResponse, SimpleCookie, StreamingHttpResponse
from django.http.request import MediaType

from pytest_undine.client import AsyncGraphQLClient
from tests.helpers import AccessLogAdd, AccessLogDelete, AccessLogGet
from undine import Entrypoint, RootType, create_schema
from undine.integrations.channels import GraphQLSSESingleConnectionConsumer
from undine.typing import DjangoTestClientResponseProtocol, PingMessage, PongMessage, SSEState, SSEStreamState

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.django_db(transaction=True),  # For sessions
]


# WebSocket


async def test_channels__websocket__connection_init(graphql) -> None:
    async with graphql.websocket() as websocket:
        result = await websocket.connection_init()

    assert result["type"] == "connection_ack"


async def test_channels__websocket__ping(graphql) -> None:
    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        ping = PingMessage(type="ping")
        result = await websocket.send_and_receive(ping)

    assert result["type"] == "pong"


async def test_channels__websocket__pong(graphql) -> None:
    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        ping = PongMessage(type="pong")
        await websocket.send(ping)


async def test_channels__websocket__subscribe(graphql, undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        operation_id = "1"
        data = {"query": "query { test }"}

        result = await websocket.subscribe(data, operation_id=operation_id)
        assert result["type"] == "next"
        assert result["id"] == operation_id
        assert result["payload"] == {"data": {"test": "Hello, World!"}}

        result = await websocket.receive()
        assert result["type"] == "complete"
        assert result["id"] == operation_id


# SSE


async def sse_sc_request(
    client: AsyncGraphQLClient,
    /,
    *,
    path="/graphql",
    body: str = "",
    method: Literal["GET", "POST", "PUT", "DELETE"] = "GET",
    headers: dict[str, str] | None = None,
) -> DjangoTestClientResponseProtocol:
    """
    Send a GraphQL over SSE request in single connection mode.

    :param body: The body of the request.
    :param method: The HTTP method of the request.
    :param headers: Additional headers for the request.
    """
    # From 'django.test.client.AsyncRequestFactory._base_scope'
    cookies = (f"{morsel.key}={morsel.coded_value}".encode("ascii") for morsel in client.cookies.values())
    result = urlsplit(path)
    scope = HTTPScope(
        type="http",
        asgi=ASGIVersions(version="3.0", spec_version="1.0"),
        http_version="1.1",
        method=method,
        scheme="http",
        path=result.path,
        raw_path=result.path.encode("utf-8"),
        query_string=result.query.encode("utf-8"),
        root_path="",
        headers=[
            (b"cookie", b"; ".join(sorted(cookies))),
            (b"host", b"testserver"),
            *[(name.lower().encode("ascii"), value.encode("latin1")) for name, value in headers.items()],
        ],
        client=("127.0.0.1", 0),
        server=("testserver", 80),
        state={},
        extensions={},
    )

    is_streaming: bool = False
    status_code: int | None = None
    response_headers: dict[str, str] = {}
    response_body: list[bytes] = []

    async def receive() -> ASGIReceiveEvent:  # noqa: RUF029
        return HTTPRequestEvent(type="http.request", body=body.encode("utf-8"), more_body=False)

    async def send(event: HTTPResponseStartEvent | HTTPResponseBodyEvent) -> None:  # noqa: RUF029
        nonlocal status_code, is_streaming

        match event["type"]:
            case "http.response.start":
                status_code = event["status"]

                for name, value in event["headers"]:
                    name_str = name.decode("ascii")
                    value_str = value.decode("latin1")
                    response_headers[name_str] = value_str

                content_type = response_headers.get("Content-Type")
                if content_type is not None and MediaType(content_type).match("text/event-stream"):
                    is_streaming = True
                    # Too much trouble to test the event stream properly,so just end the stream immediately.
                    task.cancel()

            case "http.response.body":
                response_body.append(event["body"])

            case _:
                msg = f"Unexpected event: {event['type']}"
                raise RuntimeError(msg)

    stack = AuthMiddlewareStack(GraphQLSSESingleConnectionConsumer.as_asgi())

    task = asyncio.create_task(stack(scope, receive, send))
    with suppress(asyncio.CancelledError):
        await task

    if is_streaming:
        stream = (part.decode("utf-8") for part in response_body)
        response = StreamingHttpResponse(stream, status=status_code, headers=response_headers)
    else:
        response = HttpResponse(content=b"".join(response_body), status=status_code, headers=response_headers)

    response.client = client
    response.request = scope
    response.templates = []
    response.context = {}
    response.json = partial(client._parse_json, response)

    if "Set-Cookie" in response.headers:
        response.cookies = SimpleCookie(response.headers["Set-Cookie"])
        client.cookies.update(response.cookies)

    return response  # type: ignore[return-value]


async def test_channels__sse__reserve_stream(graphql_async, undine_settings) -> None:
    await graphql_async.login_with_regular_user()

    test_uuid = uuid.uuid4()

    with patch("uuid.uuid4", return_value=test_uuid):
        response = await sse_sc_request(graphql_async, method="PUT", headers={"Accept": "text/plain"})

    assert response.status_code == HTTPStatus.CREATED
    assert response.text == test_uuid.hex

    session = await graphql_async.asession()
    session_data = await session.aload()

    state = SSEStreamState(state=SSEState.REGISTERED, stream_token=test_uuid.hex)
    assert session_data[undine_settings.SSE_STREAM_SESSION_KEY] == state


async def test_channels__sse__reserve_stream__unauthenticated(graphql_async) -> None:
    response = await sse_sc_request(graphql_async, method="PUT", headers={"Accept": "text/plain"})

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "GraphQL over SSE requires authentication in single connection mode",
                "extensions": {
                    "status_code": 401,
                    "error_code": "SSE_SINGLE_CONNECTION_NOT_AUTHENTICATED",
                },
            }
        ],
    }


async def test_channels__sse__reserve_stream__already_reserved(graphql_async, undine_settings) -> None:
    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    state = SSEStreamState(state=SSEState.REGISTERED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.asave()

    response = await sse_sc_request(graphql_async, method="PUT", headers={"Accept": "text/plain"})

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Stream already registered",
                "extensions": {
                    "error_code": "SSE_STREAM_ALREADY_REGISTERED",
                    "status_code": 409,
                },
            }
        ],
    }


async def test_channels__sse__get_stream(graphql_async, undine_settings, session_logger) -> None:
    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    state = SSEStreamState(state=SSEState.REGISTERED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.asave()

    headers = {
        "Accept": "text/event-stream",
        undine_settings.SSE_TOKEN_HEADER_NAME: stream_token,
    }

    session_logger.clear()

    response = await sse_sc_request(graphql_async, method="POST", headers=headers)

    assert isinstance(response, StreamingHttpResponse)

    graphql_logs = [log for log in session_logger if log.key.startswith("graphql")]
    assert len(graphql_logs) == 5

    stream_key = undine_settings.SSE_STREAM_SESSION_KEY
    stream_state_before = SSEStreamState(state=SSEState.REGISTERED, stream_token=stream_token)
    stream_state_after = SSEStreamState(state=SSEState.OPENED, stream_token=stream_token)

    # State from `session.load()`
    assert graphql_logs[0] == AccessLogAdd(key=stream_key, value=stream_state_before)

    # Get the session state for checking that stream exists
    assert graphql_logs[1] == AccessLogGet(key=stream_key, value=stream_state_before)

    # Update stream to opened
    assert graphql_logs[2] == AccessLogAdd(key=stream_key, value=stream_state_after)

    # Delete stream from the session (pop does get+delete)
    assert graphql_logs[3] == AccessLogGet(key=stream_key, value=stream_state_after)
    assert graphql_logs[4] == AccessLogDelete(key=stream_key)


async def test_channels__sse__get_stream__unauthenticated(graphql_async, undine_settings) -> None:
    stream_token = uuid.uuid4().hex
    state = SSEStreamState(state=SSEState.REGISTERED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.asave()

    headers = {
        "Accept": "text/event-stream",
        undine_settings.SSE_TOKEN_HEADER_NAME: stream_token,
    }
    response = await sse_sc_request(graphql_async, method="POST", headers=headers)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "GraphQL over SSE requires authentication in single connection mode",
                "extensions": {
                    "status_code": 401,
                    "error_code": "SSE_SINGLE_CONNECTION_NOT_AUTHENTICATED",
                },
            }
        ],
    }


async def test_channels__sse__get_stream__already_open(graphql_async, undine_settings) -> None:
    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    state = SSEStreamState(state=SSEState.OPENED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.asave()

    headers = {
        "Accept": "text/event-stream",
        undine_settings.SSE_TOKEN_HEADER_NAME: stream_token,
    }
    response = await sse_sc_request(graphql_async, method="POST", headers=headers)

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Stream already open",
                "extensions": {
                    "error_code": "SSE_STREAM_ALREADY_OPEN",
                    "status_code": 409,
                },
            }
        ],
    }


async def test_channels__sse__get_stream__stream_not_registered(graphql_async, undine_settings) -> None:
    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex

    headers = {
        "Accept": "text/event-stream",
        undine_settings.SSE_TOKEN_HEADER_NAME: stream_token,
    }
    response = await sse_sc_request(graphql_async, method="POST", headers=headers)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Stream not found",
                "extensions": {
                    "error_code": "SSE_STREAM_NOT_FOUND",
                    "status_code": 404,
                },
            }
        ],
    }


async def test_channels__sse__get_stream__wrong_stream_token(graphql_async, undine_settings) -> None:
    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    state = SSEStreamState(state=SSEState.OPENED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.asave()

    headers = {
        "Accept": "text/event-stream",
        undine_settings.SSE_TOKEN_HEADER_NAME: uuid.uuid4().hex,
    }
    response = await sse_sc_request(graphql_async, method="POST", headers=headers)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Stream not found",
                "extensions": {
                    "error_code": "SSE_STREAM_NOT_FOUND",
                    "status_code": 404,
                },
            }
        ],
    }


async def test_channels__sse__get_stream__stream_token_missing(graphql_async, undine_settings) -> None:
    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    state = SSEStreamState(state=SSEState.OPENED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.asave()

    headers = {
        "Accept": "text/event-stream",
    }
    response = await sse_sc_request(graphql_async, method="POST", headers=headers)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Stream token missing",
                "extensions": {
                    "error_code": "SSE_STREAM_TOKEN_MISSING",
                    "status_code": 400,
                },
            }
        ],
    }


@freezegun.freeze_time(datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC))
async def test_channels__sse__subscribe(graphql_async, undine_settings, session_logger) -> None:
    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncIterator[int]:
            for i in range(10):
                await asyncio.sleep(0.1)
                yield i

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    state = SSEStreamState(state=SSEState.OPENED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.asave()

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        undine_settings.SSE_TOKEN_HEADER_NAME: stream_token,
    }

    operation_id = "1"
    data = {
        "query": "subscription { countdown }",
        "extensions": {
            "operationId": operation_id,
        },
    }
    body = json.dumps(data, separators=(",", ":"))

    session_logger.clear()

    response = await sse_sc_request(graphql_async, body=body, method="POST", headers=headers)

    assert response.status_code == HTTPStatus.ACCEPTED, response.json()

    graphql_logs = [log for log in session_logger if log.key.startswith("graphql")]
    assert len(graphql_logs) == 5

    stream_key = undine_settings.SSE_STREAM_SESSION_KEY
    operation_key = f"{stream_key}|{operation_id}"
    stream_state = SSEStreamState(state=SSEState.OPENED, stream_token=stream_token)

    # State from `session.load()`
    assert graphql_logs[0] == AccessLogAdd(key=stream_key, value=stream_state)

    # Get the session state for checking that stream exists
    assert graphql_logs[1] == AccessLogGet(key=stream_key, value=stream_state)

    # Set operation to session
    assert graphql_logs[2] == AccessLogAdd(key=operation_key, value="2025-01-01T00:00:00+00:00")

    # Delete operation from session (pop does get+delete)
    assert graphql_logs[3] == AccessLogGet(key=operation_key, value="2025-01-01T00:00:00+00:00")
    assert graphql_logs[4] == AccessLogDelete(key=operation_key)


async def test_channels__sse__subscribe__unauthenticated(graphql_async, undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncIterator[int]:
            for i in range(10):
                await asyncio.sleep(0.1)
                yield i

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    stream_token = uuid.uuid4().hex
    state = SSEStreamState(state=SSEState.OPENED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.asave()

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        undine_settings.SSE_TOKEN_HEADER_NAME: stream_token,
    }

    data = {
        "query": "subscription { countdown }",
        "extensions": {
            "operationId": "1",
        },
    }
    body = json.dumps(data, separators=(",", ":"))

    response = await sse_sc_request(graphql_async, body=body, method="POST", headers=headers)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "GraphQL over SSE requires authentication in single connection mode",
                "extensions": {
                    "status_code": 401,
                    "error_code": "SSE_SINGLE_CONNECTION_NOT_AUTHENTICATED",
                },
            }
        ],
    }


async def test_channels__sse__subscribe__stream_not_registered(graphql_async, undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncIterator[int]:
            for i in range(10):
                await asyncio.sleep(0.1)
                yield i

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        undine_settings.SSE_TOKEN_HEADER_NAME: stream_token,
    }

    data = {
        "query": "subscription { countdown }",
        "extensions": {
            "operationId": "1",
        },
    }
    body = json.dumps(data, separators=(",", ":"))

    response = await sse_sc_request(graphql_async, body=body, method="POST", headers=headers)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Stream not found",
                "extensions": {
                    "error_code": "SSE_STREAM_NOT_FOUND",
                    "status_code": 404,
                },
            }
        ],
    }


async def test_channels__sse__subscribe__stream_not_opened(graphql_async, undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncIterator[int]:
            for i in range(10):
                await asyncio.sleep(0.1)
                yield i

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    state = SSEStreamState(state=SSEState.REGISTERED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.asave()

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        undine_settings.SSE_TOKEN_HEADER_NAME: stream_token,
    }

    data = {
        "query": "subscription { countdown }",
        "extensions": {
            "operationId": "1",
        },
    }
    body = json.dumps(data, separators=(",", ":"))

    response = await sse_sc_request(graphql_async, body=body, method="POST", headers=headers)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Stream not found",
                "extensions": {
                    "error_code": "SSE_STREAM_NOT_FOUND",
                    "status_code": 404,
                },
            }
        ],
    }


async def test_channels__sse__subscribe__wrong_stream_token(graphql_async, undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncIterator[int]:
            for i in range(10):
                await asyncio.sleep(0.1)
                yield i

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    state = SSEStreamState(state=SSEState.REGISTERED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.asave()

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        undine_settings.SSE_TOKEN_HEADER_NAME: uuid.uuid4().hex,
    }

    data = {
        "query": "subscription { countdown }",
        "extensions": {
            "operationId": "1",
        },
    }
    body = json.dumps(data, separators=(",", ":"))

    response = await sse_sc_request(graphql_async, body=body, method="POST", headers=headers)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Stream not found",
                "extensions": {
                    "error_code": "SSE_STREAM_NOT_FOUND",
                    "status_code": 404,
                },
            }
        ],
    }


async def test_channels__sse__subscribe__stream_token_missing(graphql_async, undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncIterator[int]:
            for i in range(10):
                await asyncio.sleep(0.1)
                yield i

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    state = SSEStreamState(state=SSEState.REGISTERED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.asave()

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    data = {
        "query": "subscription { countdown }",
        "extensions": {
            "operationId": "1",
        },
    }
    body = json.dumps(data, separators=(",", ":"))

    response = await sse_sc_request(graphql_async, body=body, method="POST", headers=headers)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Stream token missing",
                "extensions": {
                    "error_code": "SSE_STREAM_TOKEN_MISSING",
                    "status_code": 400,
                },
            }
        ],
    }


async def test_channels__sse__subscribe__operation_id_missing(graphql_async, undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncIterator[int]:
            for i in range(10):
                await asyncio.sleep(0.1)
                yield i

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    state = SSEStreamState(state=SSEState.OPENED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.asave()

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        undine_settings.SSE_TOKEN_HEADER_NAME: stream_token,
    }

    data = {
        "query": "subscription { countdown }",
    }
    body = json.dumps(data, separators=(",", ":"))

    response = await sse_sc_request(graphql_async, body=body, method="POST", headers=headers)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Operation ID is missing",
                "extensions": {
                    "error_code": "SSE_OPERATION_ID_MISSING",
                    "status_code": 400,
                },
            }
        ],
    }


async def test_channels__sse__subscribe__operation_already_exists(graphql_async, undine_settings) -> None:
    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncIterator[int]:
            for i in range(10):
                await asyncio.sleep(0.1)
                yield i

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    operation_id = "1"
    now = datetime.datetime.now(tz=datetime.UTC).isoformat(timespec="seconds")

    state = SSEStreamState(state=SSEState.OPENED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.aset(f"{undine_settings.SSE_STREAM_SESSION_KEY}|{operation_id}", now)
    await session.asave()

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        undine_settings.SSE_TOKEN_HEADER_NAME: stream_token,
    }

    data = {
        "query": "subscription { countdown }",
        "extensions": {
            "operationId": "1",
        },
    }
    body = json.dumps(data, separators=(",", ":"))

    response = await sse_sc_request(graphql_async, body=body, method="POST", headers=headers)

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Operation with ID already exists",
                "extensions": {
                    "error_code": "SSE_OPERATION_ALREADY_EXISTS",
                    "status_code": 409,
                },
            }
        ],
    }


async def test_channels__sse__cancel_subscription(graphql_async, undine_settings) -> None:
    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    operation_id = "1"
    now = datetime.datetime.now(tz=datetime.UTC).isoformat(timespec="seconds")

    state = SSEStreamState(state=SSEState.OPENED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.aset(f"{undine_settings.SSE_STREAM_SESSION_KEY}|{operation_id}", now)
    await session.asave()

    headers = {
        undine_settings.SSE_TOKEN_HEADER_NAME: stream_token,
    }

    path = f"/graphql?operationId={operation_id}"
    response = await sse_sc_request(graphql_async, path=path, method="DELETE", headers=headers)

    assert response.status_code == HTTPStatus.OK


async def test_channels__sse__cancel_subscription__unauthenticated(graphql_async, undine_settings) -> None:
    stream_token = uuid.uuid4().hex
    operation_id = "1"
    now = datetime.datetime.now(tz=datetime.UTC).isoformat(timespec="seconds")

    state = SSEStreamState(state=SSEState.OPENED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.aset(f"{undine_settings.SSE_STREAM_SESSION_KEY}|{operation_id}", now)
    await session.asave()

    headers = {
        undine_settings.SSE_TOKEN_HEADER_NAME: stream_token,
    }

    path = f"/graphql?operationId={operation_id}"
    response = await sse_sc_request(graphql_async, path=path, method="DELETE", headers=headers)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "GraphQL over SSE requires authentication in single connection mode",
                "extensions": {
                    "status_code": 401,
                    "error_code": "SSE_SINGLE_CONNECTION_NOT_AUTHENTICATED",
                },
            }
        ],
    }


async def test_channels__sse__cancel_subscription__operation_id_missing(graphql_async, undine_settings) -> None:
    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    operation_id = "1"
    now = datetime.datetime.now(tz=datetime.UTC).isoformat(timespec="seconds")

    state = SSEStreamState(state=SSEState.OPENED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.aset(f"{undine_settings.SSE_STREAM_SESSION_KEY}|{operation_id}", now)
    await session.asave()

    headers = {
        undine_settings.SSE_TOKEN_HEADER_NAME: stream_token,
    }

    path = "/graphql"
    response = await sse_sc_request(graphql_async, path=path, method="DELETE", headers=headers)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Operation ID is missing",
                "extensions": {
                    "error_code": "SSE_OPERATION_ID_MISSING",
                    "status_code": 400,
                },
            }
        ],
    }


async def test_channels__sse__cancel_subscription__operation_not_found(graphql_async, undine_settings) -> None:
    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    operation_id = "1"
    datetime.datetime.now(tz=datetime.UTC).isoformat(timespec="seconds")

    state = SSEStreamState(state=SSEState.OPENED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.asave()

    headers = {
        undine_settings.SSE_TOKEN_HEADER_NAME: stream_token,
    }

    path = f"/graphql?operationId={operation_id}"
    response = await sse_sc_request(graphql_async, path=path, method="DELETE", headers=headers)

    # Delete should be a no-op if operation is not found so that it is idempotent.
    assert response.status_code == HTTPStatus.OK


async def test_channels__sse__cancel_subscription__stream_not_registered(graphql_async, undine_settings) -> None:
    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    operation_id = "1"

    headers = {
        undine_settings.SSE_TOKEN_HEADER_NAME: stream_token,
    }

    path = f"/graphql?operationId={operation_id}"
    response = await sse_sc_request(graphql_async, path=path, method="DELETE", headers=headers)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Stream not found",
                "extensions": {"error_code": "SSE_STREAM_NOT_FOUND", "status_code": 404},
            }
        ],
    }


async def test_channels__sse__cancel_subscription__stream_not_opened(graphql_async, undine_settings) -> None:
    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    operation_id = "1"
    now = datetime.datetime.now(tz=datetime.UTC).isoformat(timespec="seconds")

    state = SSEStreamState(state=SSEState.REGISTERED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.aset(f"{undine_settings.SSE_STREAM_SESSION_KEY}|{operation_id}", now)
    await session.asave()

    headers = {
        undine_settings.SSE_TOKEN_HEADER_NAME: stream_token,
    }

    path = f"/graphql?operationId={operation_id}"
    response = await sse_sc_request(graphql_async, path=path, method="DELETE", headers=headers)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Stream not found",
                "extensions": {"error_code": "SSE_STREAM_NOT_FOUND", "status_code": 404},
            }
        ],
    }


async def test_channels__sse__cancel_subscription__wrong_stream_token(graphql_async, undine_settings) -> None:
    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    operation_id = "1"
    now = datetime.datetime.now(tz=datetime.UTC).isoformat(timespec="seconds")

    state = SSEStreamState(state=SSEState.OPENED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.aset(f"{undine_settings.SSE_STREAM_SESSION_KEY}|{operation_id}", now)
    await session.asave()

    headers = {
        undine_settings.SSE_TOKEN_HEADER_NAME: uuid.uuid4().hex,
    }

    path = f"/graphql?operationId={operation_id}"
    response = await sse_sc_request(graphql_async, path=path, method="DELETE", headers=headers)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Stream not found",
                "extensions": {"error_code": "SSE_STREAM_NOT_FOUND", "status_code": 404},
            }
        ],
    }


async def test_channels__sse__cancel_subscription__stream_token_missing(graphql_async, undine_settings) -> None:
    await graphql_async.login_with_regular_user()

    stream_token = uuid.uuid4().hex
    operation_id = "1"
    now = datetime.datetime.now(tz=datetime.UTC).isoformat(timespec="seconds")

    state = SSEStreamState(state=SSEState.OPENED, stream_token=stream_token)

    session = await graphql_async.asession()
    await session.aset(undine_settings.SSE_STREAM_SESSION_KEY, state)
    await session.aset(f"{undine_settings.SSE_STREAM_SESSION_KEY}|{operation_id}", now)
    await session.asave()

    headers = {}

    path = f"/graphql?operationId={operation_id}"
    response = await sse_sc_request(graphql_async, path=path, method="DELETE", headers=headers)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Stream token missing",
                "extensions": {"error_code": "SSE_STREAM_TOKEN_MISSING", "status_code": 400},
            }
        ],
    }
