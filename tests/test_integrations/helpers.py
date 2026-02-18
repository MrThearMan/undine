from __future__ import annotations

import json
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, NotRequired, Protocol, TypedDict
from unittest.mock import AsyncMock

from asgiref.testing import ApplicationCommunicator
from asgiref.typing import ASGIVersions, HTTPRequestEvent, HTTPScope
from channels.auth import AuthMiddlewareStack
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.backends.db import SessionStore
from graphql import FormattedExecutionResult

from undine.integrations.channels import GraphQLSSERouter, GraphQLSSESingleConnectionConsumer
from undine.settings import undine_settings
from undine.typing import SSEState

if TYPE_CHECKING:
    from django.contrib.sessions.backends.base import SessionBase


def make_scope(
    *,
    path: str | None = None,
    method: str = "GET",
    http_version: str = "1.1",
    headers: list[tuple[bytes, bytes]] | None = None,
    query_string: bytes = b"",
) -> HTTPScope:
    if path is None:
        path = "/" + undine_settings.GRAPHQL_PATH.removeprefix("/").removesuffix("/") + "/"

    return HTTPScope(
        type="http",
        asgi=ASGIVersions(version="3.0", spec_version="1.0"),
        http_version=http_version,
        method=method,
        path=path,
        raw_path=path.encode(),
        root_path="",
        scheme="http",
        query_string=query_string,
        headers=headers or [],
        server=("localhost", 8000),
        extensions=None,
        client=None,
    )


def make_sse_scope(
    *,
    method: str = "GET",
    headers: list[tuple[bytes, bytes]] | None = None,
    query_string: bytes = b"",
    user: User | None = None,
    session: SessionBase | None = None,
) -> HTTPScope:
    path = "/" + undine_settings.GRAPHQL_PATH.removeprefix("/").removesuffix("/") + "/"
    scope = HTTPScope(
        type="http",
        asgi=ASGIVersions(version="3.0", spec_version="1.0"),
        http_version="1.1",
        method=method,
        path=path,
        raw_path=path.encode(),
        root_path="",
        scheme="http",
        query_string=query_string,
        headers=headers or [],
        server=("localhost", 8000),
        extensions=None,
        client=None,
    )
    if user is not None:
        scope["user"] = user  # type: ignore[typeddict-unknown-key]
    if session is not None:
        scope["session"] = session  # type: ignore[typeddict-unknown-key]
    return scope


def make_sse_communicator(
    *,
    method: str = "GET",
    headers: list[tuple[bytes, bytes]] | None = None,
    query_string: bytes = b"",
    user: User | AnonymousUser | None = None,
    session: SessionBase | None = None,
) -> ApplicationCommunicator:
    """Create an ApplicationCommunicator for testing the SSE consumer."""
    scope = make_sse_scope(
        method=method,
        headers=headers,
        query_string=query_string,
        user=user,
        session=session,
    )
    app = AuthMiddlewareStack(GraphQLSSESingleConnectionConsumer.as_asgi())
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


class MockedRouter(Protocol):
    asgi_application: AsyncMock
    sse_application: AsyncMock

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None: ...


def get_router() -> MockedRouter:
    asgi_app = AsyncMock(spec=["__call__"])
    sse_app = AsyncMock(spec=["__call__"])
    return GraphQLSSERouter(asgi_application=asgi_app, sse_application=sse_app)  # type: ignore[return-value]


async def _create_user() -> User:
    user, _ = await User.objects.aget_or_create(
        username="testuser",
        defaults={"is_active": True, "email": "test@example.com"},
    )
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
    session_key = undine_settings.SSE_STREAM_SESSION_PREFIX
    stream_state = await session.aget(session_key)
    assert stream_state is not None
    assert stream_state["state"] == SSEState.REGISTERED

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
    session_key = undine_settings.SSE_STREAM_SESSION_PREFIX
    stream_state = await session.aget(session_key)
    assert stream_state is not None
    assert stream_state["state"] == SSEState.OPENED

    assert start["type"] == "http.response.start"
    assert start["status"] == HTTPStatus.OK

    # First body event (empty, keeps connection open)
    body_event = await communicator.receive_output(timeout=3)
    assert body_event["type"] == "http.response.body"
    assert body_event.get("more_body") is True
