from __future__ import annotations

import dataclasses
import json
from contextlib import contextmanager
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    AsyncIterator,
    Generator,
    Iterable,
    Iterator,
    Literal,
    NotRequired,
    Protocol,
    TypedDict,
    Unpack,
)
from unittest.mock import AsyncMock
from urllib.parse import urlencode

import sentry_sdk
from asgiref.sync import sync_to_async
from asgiref.testing import ApplicationCommunicator
from asgiref.typing import ASGIVersions, HTTPRequestEvent, HTTPScope
from channels.auth import AuthMiddlewareStack
from ddtrace.trace import Span as DatadogSpan
from ddtrace.trace import TraceFilter as DatadogTraceFilter
from ddtrace.trace import tracer as datadog_tracer
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.backends.db import SessionStore
from graphql import ExecutionResult, FormattedExecutionResult, GraphQLError, GraphQLSchema
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sentry_sdk import traces as sentry_traces
from sentry_sdk.envelope import Envelope as SentryEnvelope
from sentry_sdk.traces import SegmentNameSource as SentrySegmentNameSource
from sentry_sdk.tracing import TransactionSource as SentryTransactionSource
from sentry_sdk.transport import Transport as SentryTransport

from tests.helpers import MockRequest
from undine import Entrypoint, RootType, create_schema
from undine.dataclasses import GraphQLHttpParams
from undine.execution import execute_graphql_http_async, execute_graphql_http_sync, execute_graphql_with_subscription
from undine.hooks import LifecycleHook
from undine.integrations.channels import GraphQLSSEOperationRouter, GraphQLSSERouter
from undine.settings import undine_settings
from undine.typing import GraphQLResult, RequestMethod, SSEState
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


# OpenTelemetry


span_exporter = InMemorySpanExporter()
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))


@contextmanager
def collect_spans() -> Iterator[list[ReadableSpan]]:
    """Collect the OpenTelemetry spans that are recorded inside the block."""
    # A tracer provider can only be set once per process.
    if not isinstance(trace.get_tracer_provider(), TracerProvider):
        trace.set_tracer_provider(tracer_provider)

    span_exporter.clear()
    spans: list[ReadableSpan] = []
    try:
        yield spans
    finally:
        spans.extend(span_exporter.get_finished_spans())
        span_exporter.clear()


def get_span(spans: list[ReadableSpan], name: str) -> ReadableSpan:
    for span in spans:
        if span.name == name:
            return span

    msg = f"No span named {name!r}. Recorded spans: {[span.name for span in spans]}"
    raise KeyError(msg)


def get_parent_span_ids(spans: list[ReadableSpan]) -> list[int | None]:
    """Span id of the parent of each span, in the order the spans finished."""
    return [span.parent.span_id if span.parent is not None else None for span in spans]


def get_span_attributes(spans: list[ReadableSpan], name: str) -> dict[str, Any]:
    span = get_span(spans, name)
    return dict(span.attributes or {})


def get_exception_events(span: ReadableSpan) -> list[dict[str, Any]]:
    return [
        {
            "name": event.name,
            "type": (event.attributes or {}).get("exception.type"),
            "message": (event.attributes or {}).get("exception.message"),
        }
        for event in span.events
    ]


class Person(TypedDict):
    name: str


def build_telemetry_schema() -> GraphQLSchema:
    """Schema with sync, async and failing resolvers for testing telemetry hooks."""

    class Query(RootType):
        @Entrypoint
        def greeting(self) -> str:
            return "hello"

        @Entrypoint
        async def async_greeting(self) -> str:
            return "async hello"

        @Entrypoint
        def boom(self) -> str | None:
            msg = "kaboom"
            raise GraphQLError(msg)

        @Entrypoint
        async def async_boom(self) -> str | None:
            msg = "async kaboom"
            raise GraphQLError(msg)

        @Entrypoint
        def crash(self) -> str | None:
            msg = "the database is on fire"
            raise RuntimeError(msg)

        @Entrypoint
        async def async_crash(self) -> str | None:
            msg = "the async database is on fire"
            raise RuntimeError(msg)

        @Entrypoint
        def echo(self, value: str) -> str:
            return value

        @Entrypoint
        def people(self) -> list[Person] | None:
            return [Person(name="Ada"), Person(name="Grace")]

    class Mutation(RootType):
        @Entrypoint
        def shout(self) -> str:
            return "HELLO"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncGenerator[int, None]:
            for value in range(2, 0, -1):
                yield value

    return create_schema(query=Query, mutation=Mutation, subscription=Subscription)


class StepBoomError(Exception):
    """Raised by test hooks to simulate an unexpected failure during a lifecycle step."""


class ParseStepBoomHook(LifecycleHook):
    """Test-only hook that fails after parsing succeeds, to exercise other hooks' failure handling."""

    def on_parse(self) -> Generator[None, None, None]:
        yield
        raise StepBoomError


class ValidationStepBoomHook(LifecycleHook):
    """Test-only hook that fails after validation succeeds, to exercise other hooks' failure handling."""

    def on_validation(self) -> Generator[None, None, None]:
        yield
        raise StepBoomError


class ExecutionStepBoomHook(LifecycleHook):
    """Test-only hook that fails after execution succeeds, to exercise other hooks' failure handling."""

    def on_execution(self) -> Generator[None, None, None]:
        yield
        raise StepBoomError


def run_telemetry_query_sync(
    document: str,
    *,
    variables: dict[str, Any] | None = None,
    operation_name: str | None = None,
) -> ExecutionResult:
    params = GraphQLHttpParams(
        document=document,
        variables=variables or {},
        operation_name=operation_name,
        extensions={},
    )
    return execute_graphql_http_sync(params=params, request=MockRequest(method="POST"))


async def run_telemetry_query_async(
    document: str,
    *,
    variables: dict[str, Any] | None = None,
    operation_name: str | None = None,
) -> GraphQLResult:
    params = GraphQLHttpParams(
        document=document,
        variables=variables or {},
        operation_name=operation_name,
        extensions={},
    )
    return await execute_graphql_http_async(params=params, request=MockRequest(method="POST"))


async def run_telemetry_subscription(document: str) -> list[ExecutionResult]:
    params = GraphQLHttpParams(
        document=document,
        variables={},
        operation_name=None,
        extensions={},
    )
    stream = await execute_graphql_with_subscription(params=params, request=MockRequest(method="WEBSOCKET"))
    assert isinstance(stream, AsyncIterator), f"{stream=}"
    return [result async for result in stream]


# Datadog


class _DatadogSpanCollector(DatadogTraceFilter):
    """Collects finished traces instead of forwarding them to the (non-existent) agent."""

    def __init__(self) -> None:
        self.traces: list[list[DatadogSpan]] = []

    def process_trace(self, trace: list[DatadogSpan]) -> list[DatadogSpan] | None:
        self.traces.append(trace)
        return None  # Drop the trace instead of forwarding it to the writer.


_datadog_span_collector = _DatadogSpanCollector()
datadog_tracer.configure(trace_processors=[_datadog_span_collector])

_DATADOG_NOISE_TAGS = {"runtime-id", "language"}


@contextmanager
def collect_datadog_spans() -> Iterator[list[DatadogSpan]]:
    """Collect the Datadog spans that are recorded inside the block."""
    _datadog_span_collector.traces.clear()
    spans: list[DatadogSpan] = []
    try:
        yield spans
    finally:
        for trace in _datadog_span_collector.traces:
            spans.extend(trace)
        _datadog_span_collector.traces.clear()


def get_datadog_span(spans: list[DatadogSpan], name: str) -> DatadogSpan:
    for span in spans:
        if span.name == name:
            return span

    msg = f"No span named {name!r}. Recorded spans: {[span.name for span in spans]}"
    raise KeyError(msg)


def get_datadog_span_tags(span: DatadogSpan) -> dict[str, str]:
    tags = span.get_tags()
    return {key: value for key, value in tags.items() if not key.startswith("_dd.") and key not in _DATADOG_NOISE_TAGS}


# Sentry


SENTRY_DSN: str = "https://public@example.com/1"
"""A syntactically valid DSN. Nothing is sent anywhere, since the tests use a collecting transport."""

SENTRY_HTTP_TRANSACTION_NAME: str = "/graphql/"
"""Transaction name Sentry's Django integration would give the request before the hook renames it."""

_SENTRY_NOISE_SPAN_DATA = {"thread.id", "thread.name"}

_SENTRY_NOISE_SPAN_ATTRIBUTES = {
    "process.command_args",
    "process.runtime.name",
    "process.runtime.version",
    "sentry.environment",
    "sentry.platform",
    "sentry.release",
    "sentry.sdk.integrations",
    "sentry.sdk.name",
    "sentry.sdk.version",
    "sentry.segment.id",
    "sentry.segment.name",
    "sentry.trace_lifecycle",
    "server.address",
    "thread.id",
    "thread.name",
}


@dataclasses.dataclass(kw_only=True, slots=True)
class SentryPayloads:
    """The payloads Sentry recorded during a block, split by the kind of payload."""

    events: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    transactions: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    streamed_spans: list[dict[str, Any]] = dataclasses.field(default_factory=list)


class _SentryPayloadCollector(SentryTransport):
    """Collects envelopes instead of sending them to Sentry."""

    def __init__(self) -> None:
        super().__init__({"dsn": SENTRY_DSN})
        self.payloads = SentryPayloads()

    def capture_envelope(self, envelope: SentryEnvelope) -> None:
        for item in envelope.items:
            if item.type == "transaction":
                self.payloads.transactions.append(item.payload.json)
            elif item.type == "event":
                self.payloads.events.append(item.payload.json)
            elif item.type == "span":
                self.payloads.streamed_spans.extend(item.payload.json["items"])


@contextmanager
def _sentry_client(**client_options: Any) -> Iterator[SentryPayloads]:
    transport = _SentryPayloadCollector()
    client_options.setdefault("default_integrations", False)
    client_options.setdefault("traces_sample_rate", 1.0)

    with sentry_sdk.isolation_scope() as isolation_scope:
        client = sentry_sdk.Client(
            dsn=SENTRY_DSN,
            transport=transport,
            **client_options,
        )
        isolation_scope.set_client(client)
        try:
            yield transport.payloads
        finally:
            client.flush()


@contextmanager
def collect_sentry_payloads(**client_options: Any) -> Iterator[SentryPayloads]:
    """
    Collect the Sentry payloads that are recorded inside the block.

    A transaction is started for the block, since Sentry's Django integration starts one for
    the request, and Sentry only records spans that belong to a transaction.
    """
    with (
        _sentry_client(**client_options) as payloads,
        sentry_sdk.start_transaction(
            name=SENTRY_HTTP_TRANSACTION_NAME,
            op="http.server",
            source=SentryTransactionSource.URL,
        ),
    ):
        yield payloads


@contextmanager
def collect_sentry_payloads_without_a_transaction(**client_options: Any) -> Iterator[SentryPayloads]:
    """
    Same as `collect_sentry_payloads`, but with no transaction started for the block.

    Sentry's integrations start a transaction for an HTTP request, but not for the WebSocket and
    SSE connections that subscriptions run on.
    """
    with _sentry_client(**client_options) as payloads:
        yield payloads


@contextmanager
def collect_sentry_payloads_without_tracing(**client_options: Any) -> Iterator[SentryPayloads]:
    """Same as `collect_sentry_payloads`, but for an application that only uses Sentry for issues."""
    with _sentry_client(traces_sample_rate=None, **client_options) as payloads:
        yield payloads


@contextmanager
def collect_sentry_payloads_with_span_streaming(**client_options: Any) -> Iterator[SentryPayloads]:
    """
    Same as `collect_sentry_payloads`, but in Sentry's span streaming mode.

    A segment is started for the block, since that is what Sentry's integrations do for
    an HTTP request in this mode.
    """
    with (
        _sentry_client(trace_lifecycle="stream", **client_options) as payloads,
        sentry_traces.start_span(
            name=SENTRY_HTTP_TRANSACTION_NAME,
            attributes={
                "sentry.op": "http.server",
                "sentry.segment.name.source": SentrySegmentNameSource.URL.value,
            },
        ),
    ):
        yield payloads


@contextmanager
def collect_sentry_payloads_with_span_streaming_without_a_segment(
    **client_options: Any,
) -> Iterator[SentryPayloads]:
    """Same as `collect_sentry_payloads_with_span_streaming`, but with no segment started."""
    with _sentry_client(trace_lifecycle="stream", **client_options) as payloads:
        yield payloads


def get_sentry_transaction(payloads: SentryPayloads) -> dict[str, Any]:
    transactions = payloads.transactions
    if len(transactions) != 1:
        msg = f"Expected exactly one transaction, got {[transaction['transaction'] for transaction in transactions]}"
        raise AssertionError(msg)
    return transactions[0]


def get_sentry_span_names(transaction: dict[str, Any]) -> list[str]:
    return [span["description"] for span in transaction["spans"]]


def get_sentry_span(transaction: dict[str, Any], name: str) -> dict[str, Any]:
    for span in transaction["spans"]:
        if span["description"] == name:
            return span

    msg = f"No span named {name!r}. Recorded spans: {get_sentry_span_names(transaction)}"
    raise KeyError(msg)


def get_sentry_span_data(span: dict[str, Any]) -> dict[str, Any]:
    data: dict[str, Any] = span.get("data", {})
    return {key: value for key, value in data.items() if key not in _SENTRY_NOISE_SPAN_DATA}


def get_sentry_streamed_span_names(payloads: SentryPayloads) -> list[str]:
    return [span["name"] for span in payloads.streamed_spans]


def get_sentry_streamed_span(payloads: SentryPayloads, name: str) -> dict[str, Any]:
    for span in payloads.streamed_spans:
        if span["name"] == name:
            return span

    msg = f"No span named {name!r}. Recorded spans: {get_sentry_streamed_span_names(payloads)}"
    raise KeyError(msg)


def get_sentry_streamed_span_attributes(span: dict[str, Any]) -> dict[str, Any]:
    """The attributes the span carries, without the ones the SDK adds to every span."""
    attributes: dict[str, Any] = span.get("attributes", {})
    return {key: value["value"] for key, value in attributes.items() if key not in _SENTRY_NOISE_SPAN_ATTRIBUTES}
