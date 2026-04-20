from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http.request import MediaType
from django.http.response import ResponseHeaders
from graphql import ExecutionResult, GraphQLError

from undine.dataclasses import CompletedEventDC, CompletedEventSC, KeepAliveSignalDC, NextEventDC, NextEventSC
from undine.exceptions import (
    GraphQLErrorGroup,
    GraphQLSSEOperationAlreadyExistsError,
    GraphQLSSEStreamAlreadyOpenError,
    GraphQLSSEStreamNotFoundError,
)
from undine.typing import SSEState
from undine.utils.graphql.server_sent_events.distinct_connections import (
    execute_graphql_sse_dc,
    result_to_sse_dc,
    with_keep_alive_dc,
)
from undine.utils.graphql.server_sent_events.single_connection import (
    GraphQLOverSSESCHandler,
    SSEClaimStore,
    SSERequest,
    SSESessionStore,
    execute_graphql_sse_sc,
    get_sse_operation_claim_key,
    get_sse_operation_key,
    get_sse_stream_claim_key,
    get_sse_stream_state_key,
    get_sse_stream_token_key,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.django_db(transaction=True),
]


async def collect(gen: AsyncIterator) -> list:
    return [item async for item in gen]


# ── distinct_connections ─────────────────────────────────────────────────────


async def test_execute_graphql_sse_dc__execution_result() -> None:
    result = ExecutionResult(data={"test": "value"})

    with patch(
        "undine.utils.graphql.server_sent_events.distinct_connections.execute_graphql_with_subscription",
        return_value=result,
    ):
        items = await collect(execute_graphql_sse_dc(params=None, request=None))  # type: ignore[arg-type]

    assert len(items) == 2
    assert isinstance(items[0], NextEventDC)
    assert items[0].data == result
    assert isinstance(items[1], CompletedEventDC)


async def test_execute_graphql_sse_dc__not_async_iterator() -> None:
    with patch(
        "undine.utils.graphql.server_sent_events.distinct_connections.execute_graphql_with_subscription",
        return_value="unexpected",
    ):
        items = await collect(execute_graphql_sse_dc(params=None, request=None))  # type: ignore[arg-type]

    assert len(items) == 2
    assert isinstance(items[0], NextEventDC)
    assert items[0].data.errors is not None
    assert isinstance(items[1], CompletedEventDC)


async def test_execute_graphql_sse_dc__async_iterator__graphql_error() -> None:
    async def fake_stream() -> AsyncIterator[ExecutionResult]:
        yield ExecutionResult(data={"a": 1})
        raise GraphQLError("stream error")

    with patch(
        "undine.utils.graphql.server_sent_events.distinct_connections.execute_graphql_with_subscription",
        return_value=fake_stream(),
    ):
        items = await collect(execute_graphql_sse_dc(params=None, request=None))  # type: ignore[arg-type]

    assert len(items) == 3
    assert isinstance(items[1], NextEventDC)
    assert items[1].data.errors is not None
    assert isinstance(items[2], CompletedEventDC)


async def test_execute_graphql_sse_dc__async_iterator__graphql_error_group() -> None:
    async def fake_stream() -> AsyncIterator[ExecutionResult]:
        yield ExecutionResult(data={"a": 1})
        raise GraphQLErrorGroup([GraphQLError("e1"), GraphQLError("e2")])

    with patch(
        "undine.utils.graphql.server_sent_events.distinct_connections.execute_graphql_with_subscription",
        return_value=fake_stream(),
    ):
        items = await collect(execute_graphql_sse_dc(params=None, request=None))  # type: ignore[arg-type]

    assert len(items) == 3
    assert isinstance(items[1], NextEventDC)
    assert items[1].data.errors is not None
    assert isinstance(items[2], CompletedEventDC)


async def test_execute_graphql_sse_dc__async_iterator__generic_exception() -> None:
    async def fake_stream() -> AsyncIterator[ExecutionResult]:
        yield ExecutionResult(data={"a": 1})
        raise RuntimeError("unexpected")

    with patch(
        "undine.utils.graphql.server_sent_events.distinct_connections.execute_graphql_with_subscription",
        return_value=fake_stream(),
    ):
        items = await collect(execute_graphql_sse_dc(params=None, request=None))  # type: ignore[arg-type]

    assert len(items) == 3
    assert isinstance(items[1], NextEventDC)
    assert items[1].data.errors is not None
    assert isinstance(items[2], CompletedEventDC)


async def test_result_to_sse_dc() -> None:
    result = ExecutionResult(data={"test": "value"})
    items = await collect(result_to_sse_dc(result))

    assert len(items) == 2
    assert isinstance(items[0], NextEventDC)
    assert items[0].data == result
    assert isinstance(items[1], CompletedEventDC)


async def test_with_keep_alive_dc__no_interval(undine_settings) -> None:
    undine_settings.SSE_KEEP_ALIVE_INTERVAL = 0

    async def source() -> AsyncIterator[NextEventDC | CompletedEventDC]:
        yield NextEventDC(data=ExecutionResult(data={}))
        yield CompletedEventDC()

    items = await collect(with_keep_alive_dc(source()))

    assert all(not isinstance(item, KeepAliveSignalDC) for item in items)
    assert len(items) == 2


async def test_with_keep_alive_dc__with_interval(undine_settings) -> None:
    undine_settings.SSE_KEEP_ALIVE_INTERVAL = 60

    async def source() -> AsyncIterator[NextEventDC | CompletedEventDC]:
        yield NextEventDC(data=ExecutionResult(data={}))
        yield CompletedEventDC()

    items = await collect(with_keep_alive_dc(source()))

    assert isinstance(items[0], KeepAliveSignalDC)
    assert isinstance(items[1], NextEventDC)
    assert isinstance(items[2], CompletedEventDC)


async def test_with_keep_alive_dc__cancel_on_close(undine_settings) -> None:
    undine_settings.SSE_KEEP_ALIVE_INTERVAL = 60  # Long — ensures next_event is pending

    async def source() -> AsyncIterator[NextEventDC | CompletedEventDC]:
        await asyncio.sleep(100)  # Never completes in test
        yield CompletedEventDC()

    gen = with_keep_alive_dc(source())
    first = await gen.__anext__()
    assert isinstance(first, KeepAliveSignalDC)  # initial keep-alive

    # Close generator while next_event is still pending — triggers finally: next_event.cancel()
    await gen.aclose()


async def test_with_keep_alive_dc__cancel_inside_try(undine_settings) -> None:
    """Line 99: cancel next_event in finally when closed while inside the try block."""
    undine_settings.SSE_KEEP_ALIVE_INTERVAL = 0.001  # 1ms — fires quickly

    async def source() -> AsyncIterator[NextEventDC | CompletedEventDC]:
        yield CompletedEventDC()
        await asyncio.sleep(100)  # Block after first event

    gen = with_keep_alive_dc(source())

    # 1. Initial keep-alive (before try block)
    first = await gen.__anext__()
    assert isinstance(first, KeepAliveSignalDC)

    # 2. Enter try block; next_event fires (source yields complete event)
    second = await gen.__anext__()
    assert isinstance(second, CompletedEventDC)

    # 3. New next_event pending (source is sleeping 100s), timeout fires → yields keep-alive.
    #    Generator suspended inside try block at line 89 (yield KeepAliveSignalDC()).
    third = await gen.__anext__()
    assert isinstance(third, KeepAliveSignalDC)

    # 4. Close while inside try block with pending next_event → finally: next_event.cancel() (line 99).
    await gen.aclose()


async def test_with_keep_alive_dc__heartbeat_on_timeout(undine_settings) -> None:
    undine_settings.SSE_KEEP_ALIVE_INTERVAL = 0.01  # 10ms

    event = asyncio.Event()

    async def source() -> AsyncIterator[NextEventDC | CompletedEventDC]:
        await event.wait()
        yield CompletedEventDC()

    async def drive() -> list:
        results = []
        async for item in with_keep_alive_dc(source()):
            results.append(item)
            if isinstance(item, KeepAliveSignalDC) and len(results) >= 2:
                event.set()
        return results

    items = await asyncio.wait_for(drive(), timeout=5)

    heartbeats = [i for i in items if isinstance(i, KeepAliveSignalDC)]
    assert len(heartbeats) >= 2


# ── single_connection key helpers ────────────────────────────────────────────


def test_get_sse_stream_token_key(undine_settings) -> None:
    undine_settings.SSE_STREAM_SESSION_PREFIX = "test_prefix"
    assert get_sse_stream_token_key() == "test_prefix|token"


def test_get_sse_stream_state_key(undine_settings) -> None:
    undine_settings.SSE_STREAM_SESSION_PREFIX = "test_prefix"
    assert get_sse_stream_state_key() == "test_prefix|state"


def test_get_sse_operation_key(undine_settings) -> None:
    undine_settings.SSE_STREAM_SESSION_PREFIX = "test_prefix"
    assert get_sse_operation_key(operation_id="op1") == "test_prefix|operation|op1"


def test_get_sse_stream_claim_key(undine_settings) -> None:
    undine_settings.SSE_STREAM_SESSION_PREFIX = "test_prefix"
    assert get_sse_stream_claim_key("tok") == "test_prefix|stream-claim|tok"


def test_get_sse_operation_claim_key(undine_settings) -> None:
    undine_settings.SSE_STREAM_SESSION_PREFIX = "test_prefix"
    assert get_sse_operation_claim_key("tok", "op1") == "test_prefix|operation-claim|tok|op1"


# ── execute_graphql_sse_sc ───────────────────────────────────────────────────


async def test_execute_graphql_sse_sc__execution_result() -> None:
    result = ExecutionResult(data={"test": "value"})

    with patch(
        "undine.utils.graphql.server_sent_events.single_connection.execute_graphql_with_subscription",
        return_value=result,
    ):
        items = await collect(execute_graphql_sse_sc("op1", params=None, request=None))  # type: ignore[arg-type]

    assert len(items) == 2
    assert isinstance(items[0], NextEventSC)
    assert items[0].operation_id == "op1"
    assert items[0].payload == result
    assert isinstance(items[1], CompletedEventSC)


async def test_execute_graphql_sse_sc__not_async_iterator() -> None:
    with patch(
        "undine.utils.graphql.server_sent_events.single_connection.execute_graphql_with_subscription",
        return_value="unexpected",
    ):
        items = await collect(execute_graphql_sse_sc("op1", params=None, request=None))  # type: ignore[arg-type]

    assert len(items) == 2
    assert isinstance(items[0], NextEventSC)
    assert items[0].payload.errors is not None
    assert isinstance(items[1], CompletedEventSC)


async def test_execute_graphql_sse_sc__graphql_error() -> None:
    async def fake_stream() -> AsyncIterator[ExecutionResult]:
        yield ExecutionResult(data={"a": 1})
        raise GraphQLError("stream error")

    with patch(
        "undine.utils.graphql.server_sent_events.single_connection.execute_graphql_with_subscription",
        return_value=fake_stream(),
    ):
        items = await collect(execute_graphql_sse_sc("op1", params=None, request=None))  # type: ignore[arg-type]

    assert len(items) == 3
    assert isinstance(items[1], NextEventSC)
    assert items[1].payload.errors is not None
    assert isinstance(items[2], CompletedEventSC)


async def test_execute_graphql_sse_sc__graphql_error_group() -> None:
    async def fake_stream() -> AsyncIterator[ExecutionResult]:
        yield ExecutionResult(data={"a": 1})
        raise GraphQLErrorGroup([GraphQLError("e1")])

    with patch(
        "undine.utils.graphql.server_sent_events.single_connection.execute_graphql_with_subscription",
        return_value=fake_stream(),
    ):
        items = await collect(execute_graphql_sse_sc("op1", params=None, request=None))  # type: ignore[arg-type]

    assert len(items) == 3
    assert isinstance(items[1], NextEventSC)
    assert items[1].payload.errors is not None


async def test_execute_graphql_sse_sc__generic_exception() -> None:
    async def fake_stream() -> AsyncIterator[ExecutionResult]:
        yield ExecutionResult(data={"a": 1})
        raise RuntimeError("unexpected")

    with patch(
        "undine.utils.graphql.server_sent_events.single_connection.execute_graphql_with_subscription",
        return_value=fake_stream(),
    ):
        items = await collect(execute_graphql_sse_sc("op1", params=None, request=None))  # type: ignore[arg-type]

    assert len(items) == 3
    assert isinstance(items[1], NextEventSC)
    assert items[1].payload.errors is not None


# ── SSESessionStore ──────────────────────────────────────────────────────────


def _make_session_store() -> SSESessionStore:
    session = MagicMock()
    session._session_cache = {}
    session.get = lambda key, default=None: session._session_cache.get(key, default)
    session.__contains__ = lambda self, key: key in self._session_cache
    session.keys = lambda: session._session_cache.keys()
    session.__setitem__ = lambda self, key, value: session._session_cache.__setitem__(key, value)
    session.pop = lambda key, default=None: session._session_cache.pop(key, default)
    return SSESessionStore(session=session)


async def test_sse_session_store__refresh__with_aload(undine_settings) -> None:
    store = _make_session_store()
    store.session.aload = AsyncMock(return_value={"key": "val"})

    await store.refresh()
    assert store.session._session_cache == {"key": "val"}


async def test_sse_session_store__refresh__without_aload(undine_settings) -> None:
    store = _make_session_store()
    # No 'aload' attribute
    del store.session.aload
    store.session.load = MagicMock(return_value={"key": "val2"})

    await store.refresh()
    assert store.session._session_cache == {"key": "val2"}


async def test_sse_session_store__save__with_asave(undine_settings) -> None:
    store = _make_session_store()
    store.session.asave = AsyncMock()

    await store.save()
    store.session.asave.assert_called_once()


async def test_sse_session_store__save__without_asave(undine_settings) -> None:
    store = _make_session_store()
    del store.session.asave
    store.session.save = MagicMock()

    await store.save()
    store.session.save.assert_called_once()


# ── SSERequest ───────────────────────────────────────────────────────────────


def _make_scope() -> dict:
    from asgiref.typing import HTTPScope

    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
        ],
        "path": "/graphql/",
        "raw_path": b"/graphql/",
        "query_string": b"",
        "root_path": "",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 0),
        "state": {},
        "extensions": {},
        "user": AnonymousUser(),
        "session": None,
    }


async def test_sse_request__properties() -> None:
    scope = _make_scope()
    request = SSERequest(scope=scope, messages=[])  # type: ignore[arg-type]

    assert request.GET is not None
    assert request.POST is not None
    assert request.COOKIES is not None
    assert request.FILES is not None
    assert request.META is not None
    assert request.scheme is not None
    assert request.path is not None
    assert request.method is not None
    assert request.headers is not None
    assert request.body == b""
    assert request.encoding is None or isinstance(request.encoding, str)

    assert isinstance(request.user, AnonymousUser)
    assert isinstance(await request.auser(), AnonymousUser)

    assert request.session is None
    assert request.content_type is not None or request.content_type is None
    assert request.content_params is not None or request.content_params is None
    assert isinstance(request.accepted_types, list)

    # response_content_type: first access, then cached
    ct1 = request.response_content_type
    assert ct1 is not None
    ct2 = request.response_content_type
    assert ct2 is ct1

    # setter
    new_ct = MediaType("text/plain")
    request.response_content_type = new_ct
    assert request.response_content_type is new_ct

    # response_headers: first access, then cached
    rh1 = request.response_headers
    assert isinstance(rh1, ResponseHeaders)
    rh2 = request.response_headers
    assert rh2 is rh1

    # setter
    new_rh = ResponseHeaders({})
    request.response_headers = new_rh
    assert request.response_headers is new_rh


# ── GraphQLOverSSESCHandler ──────────────────────────────────────────────────


def _make_handler() -> tuple[GraphQLOverSSESCHandler, MagicMock, SSESessionStore]:
    signaler = MagicMock()
    signaler.signal_stream_close = AsyncMock()
    signaler.register_stream = AsyncMock()
    signaler.signal_stream_open = AsyncMock()
    signaler.register_stream_open = AsyncMock()
    signaler.signal_operation_event = AsyncMock()
    signaler.signal_operation_cancel = AsyncMock()
    signaler.signal_operation_cancel_all = AsyncMock()
    signaler.unregister_stream = AsyncMock()
    signaler.unregister_stream_open = AsyncMock()
    signaler.register_operation = AsyncMock()
    signaler.unregister_operation = AsyncMock()
    signaler.release_stream_claim = AsyncMock()

    session_mock = MagicMock()
    cache: dict = {}
    session_mock._session_cache = cache
    session_mock.get = lambda key, default=None: cache.get(key, default)
    session_mock.__contains__ = lambda self, key: key in cache
    session_mock.keys = lambda: cache.keys()
    session_mock.__setitem__ = lambda self, key, value: cache.__setitem__(key, value)
    session_mock.pop = lambda key, default=None: cache.pop(key, default)
    session_mock.asave = AsyncMock()
    session_mock.aload = AsyncMock(return_value=cache)

    claims = MagicMock(spec=SSEClaimStore)
    claims.claim_stream = AsyncMock(return_value=True)
    claims.release_stream_claim = AsyncMock()
    claims.claim_operation = AsyncMock(return_value=True)
    claims.release_operation_claim = AsyncMock()

    session_store = SSESessionStore(session=session_mock)
    handler = GraphQLOverSSESCHandler(signaler=signaler, session=session_store, claims=claims)
    return handler, signaler, session_store


async def test_handler__reserve_stream__no_existing(undine_settings) -> None:
    handler, signaler, _ = _make_handler()
    token = await handler.reserve_stream()

    assert isinstance(token, str)
    assert len(token) == 32  # uuid4().hex


async def test_handler__reserve_stream__existing_opened(undine_settings) -> None:
    handler, signaler, session_store = _make_handler()

    # Pre-populate an opened stream in the session
    prefix = "undine-sse"
    undine_settings.SSE_STREAM_SESSION_PREFIX = prefix
    session_store.set_stream_token("old_token")
    session_store.set_stream_state(SSEState.OPENED)

    token = await handler.reserve_stream()

    signaler.signal_stream_close.assert_called_once_with("old_token")
    assert isinstance(token, str)


async def test_handler__open_event_stream__stream_not_found(undine_settings) -> None:
    handler, _, session_store = _make_handler()

    with pytest.raises(GraphQLSSEStreamNotFoundError):
        await handler.open_event_stream("nonexistent_token")


async def test_handler__open_event_stream__already_open(undine_settings) -> None:
    handler, _, session_store = _make_handler()
    handler.claims.claim_stream = AsyncMock(return_value=False)  # type: ignore[attr-defined]

    session_store.set_stream_token("tok")
    session_store.set_stream_state(SSEState.REGISTERED)

    with pytest.raises(GraphQLSSEStreamAlreadyOpenError):
        await handler.open_event_stream("tok")


async def test_handler__start_operation__stream_not_found(undine_settings) -> None:
    handler, _, _ = _make_handler()

    with pytest.raises(GraphQLSSEStreamNotFoundError):
        await handler.start_operation("bad_token", "op1")


async def test_handler__start_operation__already_exists(undine_settings) -> None:
    handler, _, session_store = _make_handler()
    handler.claims.claim_operation = AsyncMock(return_value=False)  # type: ignore[attr-defined]

    session_store.set_stream_token("tok")
    session_store.set_stream_state(SSEState.OPENED)
    session_store.set_operation("op1")

    with pytest.raises(GraphQLSSEOperationAlreadyExistsError):
        await handler.start_operation("tok", "op1")


async def test_handler__cancel_operation__stream_not_found(undine_settings) -> None:
    handler, _, _ = _make_handler()

    with pytest.raises(GraphQLSSEStreamNotFoundError):
        await handler.cancel_operation("bad_token", "op1")


async def test_handler__execute_operation__cancelled(undine_settings) -> None:
    handler, signaler, session_store = _make_handler()
    session_store.set_stream_token("tok")

    async def raises_cancelled(*args, **kwargs) -> AsyncIterator[NextEventSC]:
        raise asyncio.CancelledError
        yield  # make it a generator

    with patch(
        "undine.utils.graphql.server_sent_events.single_connection.execute_graphql_sse_sc",
        side_effect=raises_cancelled,
    ):
        await handler.execute_operation("tok", "op1", params=None, request=None)  # type: ignore[arg-type]

    # Should send a complete event
    signaler.signal_operation_event.assert_called()


async def test_handler__execute_operation__completed_then_exception(undine_settings) -> None:
    """Branch 302->exit: exception raised after completed=True — no extra complete event sent."""
    handler, signaler, session_store = _make_handler()
    session_store.set_stream_token("tok")

    async def yields_complete(*args, **kwargs) -> AsyncIterator[CompletedEventSC]:
        yield CompletedEventSC(operation_id="op1")

    # signal_operation_event raises CancelledError — while completed is already True
    async def signal_raises(stream_token: str, data: bytes) -> None:
        raise asyncio.CancelledError

    signaler.signal_operation_event.side_effect = signal_raises

    with patch(
        "undine.utils.graphql.server_sent_events.single_connection.execute_graphql_sse_sc",
        side_effect=yields_complete,
    ):
        await handler.execute_operation("tok", "op1", params=None, request=None)  # type: ignore[arg-type]

    # signal_operation_event called once (for the complete event) but raised;
    # because completed=True, no second complete event is sent (302->exit branch)
    signaler.signal_operation_event.assert_called_once()
