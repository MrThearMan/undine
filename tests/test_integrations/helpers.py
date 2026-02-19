from __future__ import annotations

import json
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Iterable, Literal, NotRequired, Protocol, TypedDict, Unpack
from unittest.mock import AsyncMock

from asgiref.testing import ApplicationCommunicator
from asgiref.typing import ASGIVersions, HTTPRequestEvent, HTTPScope
from channels.auth import AuthMiddlewareStack
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.backends.db import SessionStore
from graphql import FormattedExecutionResult

from undine.integrations.channels import (
    GraphQLSSEOperationRouter,
    GraphQLSSERouter,
    get_sse_stream_state_key,
    get_sse_stream_token_key,
)
from undine.settings import undine_settings
from undine.typing import RequestMethod, SSEState

if TYPE_CHECKING:
    from django.contrib.sessions.backends.base import SessionBase


class HTTPScopeArgs(TypedDict, total=False):
    http_version: Literal["1.0", "1.1", "2.0", "3.0"]
    method: RequestMethod
    scheme: Literal["http", "https"]
    path: str
    query_string: bytes
    headers: Iterable[tuple[bytes, bytes]]
    user: User | None
    session: SessionBase | None


def make_http_scope(**kwargs: Unpack[HTTPScopeArgs]) -> HTTPScope:
    if "path" not in kwargs:
        kwargs["path"] = "/" + undine_settings.GRAPHQL_PATH.removeprefix("/").removesuffix("/") + "/"

    scope = HTTPScope(
        type="http",
        asgi=ASGIVersions(version="3.0", spec_version="1.0"),
        http_version=kwargs.get("http_version", "1.1"),
        method=kwargs.get("method", "GET"),
        path=kwargs["path"],
        raw_path=kwargs["path"].encode(),
        root_path="",
        scheme=kwargs.get("scheme", "http"),
        query_string=kwargs.get("query_string", b""),
        headers=kwargs.get("headers", []),
        server=("localhost", 8000),
        extensions=None,
        client=None,
    )
    if "user" in kwargs:
        scope["user"] = kwargs["user"]  # type: ignore[typeddict-unknown-key]
    if "session" in kwargs:
        scope["session"] = kwargs["session"]  # type: ignore[typeddict-unknown-key]
    return scope


def make_sse_communicator(
    *,
    method: RequestMethod = "GET",
    headers: list[tuple[bytes, bytes]] | None = None,
    query_string: bytes = b"",
    user: User | AnonymousUser | None = None,
    session: SessionBase | None = None,
) -> ApplicationCommunicator:
    """Create an ApplicationCommunicator for testing the SSE consumer."""
    scope = make_http_scope(
        method=method,
        headers=headers or [],
        query_string=query_string,
        user=user,
        session=session,
    )
    app = AuthMiddlewareStack(GraphQLSSEOperationRouter())
    return ApplicationCommunicator(app, scope)


async def sse_send_request(communicator: ApplicationCommunicator, body: bytes = b"") -> None:
    """Send an HTTP request event to the communicator."""
    await communicator.send_input(
        HTTPRequestEvent(type="http.request", body=body, more_body=False),
    )


class SSEResponse(TypedDict):
    status: int
    headers: dict[str, str]
    body: NotRequired[bytes]
    json: NotRequired[FormattedExecutionResult]


async def sse_get_response(communicator: ApplicationCommunicator) -> SSEResponse:
    """Get a complete HTTP response (start + body) from the communicator."""
    start = await communicator.receive_output(timeout=3)
    assert start["type"] == "http.response.start"

    body_event = await communicator.receive_output(timeout=3)
    assert body_event["type"] == "http.response.body"

    status = start["status"]
    headers = {k.decode(): v.decode() for k, v in start.get("headers", [])}
    body = body_event.get("body", b"")

    result: SSEResponse = {"status": status, "headers": headers}
    if headers.get("Content-Type", "").startswith("application/json"):
        result["json"] = json.loads(body)
    else:
        result["body"] = body.decode() if isinstance(body, bytes) else body

    return result


class MockedGraphQLSSERouter(Protocol):
    django_application: AsyncMock
    sse_application: AsyncMock

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None: ...


def get_graphql_sse_router() -> MockedGraphQLSSERouter:
    router = GraphQLSSERouter(django_application=AsyncMock(spec=["__call__"]))
    router.sse_application = AsyncMock(spec=["__call__"])
    return router  # type: ignore[return-value]


class MockedGraphQLSSEOperationRouter(Protocol):
    stream_reservation_consumer: AsyncMock
    event_stream_consumer: AsyncMock
    operation_consumer: AsyncMock
    operation_cancellation_consumer: AsyncMock
    send_http_response: AsyncMock

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None: ...


def get_graphql_sse_operation_router() -> MockedGraphQLSSEOperationRouter:
    router = GraphQLSSEOperationRouter()
    router.stream_reservation_consumer = AsyncMock(spec=["__call__"])
    router.event_stream_consumer = AsyncMock(spec=["__call__"])
    router.operation_consumer = AsyncMock(spec=["__call__"])
    router.operation_cancellation_consumer = AsyncMock(spec=["__call__"])
    router.send_http_response = AsyncMock(spec=["__call__"])
    return router  # type: ignore[return-value]


async def _create_user() -> User:
    defaults = {"is_active": True, "email": "test@example.com"}
    user, _ = await User.objects.aget_or_create(username="testuser", defaults=defaults)
    return user


async def _create_session(user: User | None = None) -> SessionStore:
    session = SessionStore()
    if user is not None:
        session["_auth_user_id"] = str(user.pk)
        session["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
    await session.acreate()
    return session


async def _reserve_stream(user: User, session: SessionStore) -> str:
    """Helper to reserve a stream and return the token."""
    communicator = make_sse_communicator(
        method="PUT",
        headers=[(b"accept", b"text/plain")],
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    # Verify session was updated
    stream_token_key = get_sse_stream_token_key()
    stream_state_key = get_sse_stream_state_key()
    stream_token = await session.aget(stream_token_key)
    stream_state = await session.aget(stream_state_key)
    assert stream_state == SSEState.REGISTERED
    assert stream_token == response["body"]

    assert response["status"] == HTTPStatus.CREATED
    return response["body"]


async def _open_stream(user: User, session: SessionStore, token: str) -> None:
    """Helper to open a stream (GET with token) and wait for SSE headers."""
    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=f"token={token}".encode(),
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    start = await communicator.receive_output(timeout=3)

    # Verify session was updated
    stream_token_key = get_sse_stream_token_key()
    stream_state_key = get_sse_stream_state_key()
    stream_token = await session.aget(stream_token_key)
    stream_state = await session.aget(stream_state_key)
    assert stream_state == SSEState.OPENED
    assert stream_token == token

    assert start["type"] == "http.response.start"
    assert start["status"] == HTTPStatus.OK

    # First body event (SSE comment keep-alive, keeps connection open)
    body_event = await communicator.receive_output(timeout=3)
    assert body_event["type"] == "http.response.body"
    assert body_event["body"] == b":\n\n"
    assert body_event.get("more_body") is True
