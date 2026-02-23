from __future__ import annotations

import json
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Iterable, Literal, NotRequired, Protocol, TypedDict, Unpack
from unittest.mock import AsyncMock
from urllib.parse import urlencode

from asgiref.sync import sync_to_async
from asgiref.testing import ApplicationCommunicator
from asgiref.typing import ASGIVersions, HTTPRequestEvent, HTTPScope
from channels.auth import AuthMiddlewareStack
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.backends.db import SessionStore
from graphql import FormattedExecutionResult

from undine.integrations.channels import GraphQLSSEOperationRouter, GraphQLSSERouter
from undine.settings import undine_settings
from undine.typing import RequestMethod, SSEState
from undine.utils.graphql.server_sent_events import get_sse_stream_state_key, get_sse_stream_token_key

if TYPE_CHECKING:
    from django.contrib.sessions.backends.base import SessionBase


async def session_aget(session: SessionBase, key: str) -> Any:
    """Django 5.0 compat: SessionBase.aget was added in Django 5.1."""
    if hasattr(session, "aget"):
        return await session.aget(key)
    return await sync_to_async(session.get)(key)


async def session_aset(session: SessionBase, key: str, value: Any) -> None:
    """Django 5.0 compat: SessionBase.aset was added in Django 5.1."""
    if hasattr(session, "aset"):
        await session.aset(key=key, value=value)
    else:
        await sync_to_async(session.__setitem__)(key, value)


async def session_aload(session: SessionBase) -> None:
    """Django 5.0 compat: SessionBase.aload was added in Django 5.1."""
    if hasattr(session, "aload"):
        await session.aload()
    else:
        await sync_to_async(session.load)()


async def session_asave(session: SessionBase) -> None:
    """Django 5.0 compat: SessionBase.asave was added in Django 5.1."""
    if hasattr(session, "asave"):
        await session.asave()
    else:
        await sync_to_async(session.save)()


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
    body: NotRequired[str]
    json: NotRequired[FormattedExecutionResult]


async def sse_get_response(communicator: ApplicationCommunicator) -> SSEResponse:
    """Get a complete HTTP response (start + body) from the communicator."""
    start = await communicator.receive_output(timeout=3)
    assert start["type"] == "http.response.start", f"{start=}"

    body_event = await communicator.receive_output(timeout=3)
    assert body_event["type"] == "http.response.body", f"{body_event=}"

    status = start["status"]
    headers = {k.decode(): v.decode() for k, v in start.get("headers", [])}
    body = body_event.get("body", b"")

    result: SSEResponse = {"status": status, "headers": headers}
    if headers.get("Content-Type", "").startswith("application/json"):
        result["json"] = json.loads(body)
    else:
        result["body"] = body.decode() if isinstance(body, bytes) else body

    return result


class SSEEvent(TypedDict, total=False):
    event: str
    data: dict[str, Any]


async def sse_read_stream_event(communicator: ApplicationCommunicator, *, timeout: float = 5) -> SSEEvent:
    """Read one SSE event from the stream communicator and parse it."""
    output = await communicator.receive_output(timeout=timeout)
    assert output["type"] == "http.response.body", f"{output=}"
    assert output.get("more_body") is True, f"{output=}"

    raw = output["body"].decode()
    parsed: SSEEvent = {}
    for line in raw.strip().split("\n"):
        if line.startswith("event: "):
            parsed["event"] = line[len("event: ") :]
        elif line.startswith("data: "):
            parsed["data"] = json.loads(line[len("data: ") :])
    return parsed


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

    if hasattr(session, "acreate"):
        await session.acreate()
    else:
        await sync_to_async(session.create)()

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

    stream_token_key = get_sse_stream_token_key()
    stream_state_key = get_sse_stream_state_key()
    stream_token = await session_aget(session, stream_token_key)
    stream_state = await session_aget(session, stream_state_key)

    assert stream_state == SSEState.REGISTERED, f"{stream_state=}"
    assert stream_token == response["body"], f"{stream_token=}, {response['body']=}"

    assert response["status"] == HTTPStatus.CREATED, f"{response=}"
    return response["body"]


async def _open_stream(user: User, session: SessionStore, token: str) -> ApplicationCommunicator:
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

    assert start["type"] == "http.response.start", f"{start=}"
    assert start["status"] == HTTPStatus.OK, f"{start=}"

    stream_token_key = get_sse_stream_token_key()
    stream_state_key = get_sse_stream_state_key()
    stream_token = await session_aget(session, stream_token_key)
    stream_state = await session_aget(session, stream_state_key)

    assert stream_state == SSEState.OPENED, f"{stream_state=}"
    assert stream_token == token, f"{stream_token=}, {token=}"

    # First body event (SSE comment keep-alive, keeps connection open)
    body_event = await communicator.receive_output(timeout=3)
    assert body_event["type"] == "http.response.body", f"{body_event=}"
    assert body_event["body"] == b":\n\n", f"{body_event=}"
    assert body_event.get("more_body") is True, f"{body_event=}"

    return communicator


def make_operation_body(*, query: str, operation_id: str) -> bytes:
    """Encode a GraphQL operation as a JSON body for POST submission."""
    return json.dumps({
        "query": query,
        "extensions": {"operationId": operation_id},
    }).encode()


def make_sse_operation_communicator(*, user: User, session: SessionStore, token: str) -> ApplicationCommunicator:
    return make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", token.encode()),
        ],
        user=user,
        session=session,
    )


def make_sse_cancel_communicator(
    *,
    user: User,
    session: SessionStore,
    token: str,
    operation_id: str,
) -> ApplicationCommunicator:
    query_string = urlencode({"operationId": operation_id}).encode()
    return make_sse_communicator(
        method="DELETE",
        headers=[(b"x-graphql-event-stream-token", token.encode())],
        query_string=query_string,
        user=user,
        session=session,
    )


def make_sse_get_operation_communicator(
    *,
    user: User,
    session: SessionStore,
    token: str,
    query: str,
    operation_id: str,
) -> ApplicationCommunicator:
    extensions = json.dumps({"operationId": operation_id}, separators=(",", ":"))
    query_string = urlencode({"token": token, "query": query, "extensions": extensions}).encode()
    return make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"application/json")],
        query_string=query_string,
        user=user,
        session=session,
    )
