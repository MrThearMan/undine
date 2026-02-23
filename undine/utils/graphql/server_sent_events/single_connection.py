from __future__ import annotations

import asyncio
import dataclasses
import io
import uuid
from collections.abc import AsyncIterator
from contextlib import suppress
from functools import cached_property
from typing import TYPE_CHECKING, Any

from asgiref.sync import sync_to_async
from django.conf import settings as django_settings
from django.core.cache import caches
from django.core.handlers.asgi import ASGIRequest
from graphql import GraphQLError

from undine.dataclasses import CompletedEventSC, NextEventSC
from undine.exceptions import (
    GraphQLErrorGroup,
    GraphQLSSEOperationAlreadyExistsError,
    GraphQLSSEStreamAlreadyOpenError,
    GraphQLSSEStreamNotFoundError,
    GraphQLUnexpectedError,
)
from undine.execution import execute_graphql_with_subscription
from undine.settings import undine_settings
from undine.typing import SSEState
from undine.utils.graphql.utils import get_error_execution_result

if TYPE_CHECKING:
    from asgiref.typing import HTTPRequestEvent
    from django.contrib.auth.models import AnonymousUser, User
    from django.contrib.sessions.backends.base import SessionBase
    from django.core.files.uploadedfile import UploadedFile
    from django.http import HttpHeaders, QueryDict
    from django.http.request import MediaType
    from django.utils.datastructures import MultiValueDict

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol, HTTPASGIScope, RequestMethod, SSESignaler


__all__ = [
    "GraphQLOverSSESCHandler",
    "SSEClaimStore",
    "SSERequest",
    "SSESessionStore",
    "execute_graphql_sse_sc",
    "get_sse_operation_claim_key",
    "get_sse_operation_key",
    "get_sse_stream_claim_key",
    "get_sse_stream_state_key",
    "get_sse_stream_token_key",
]


async def execute_graphql_sse_sc(
    operation_id: str,
    params: GraphQLHttpParams,
    request: DjangoRequestProtocol,
) -> AsyncIterator[NextEventSC | CompletedEventSC]:
    """Execute a GraphQL operation received through server-sent events in single connection mode."""
    stream = await execute_graphql_with_subscription(params, request)

    if not isinstance(stream, AsyncIterator):
        yield NextEventSC(operation_id=operation_id, payload=stream.formatted)
        yield CompletedEventSC(operation_id=operation_id)
        return

    try:
        async for data in stream:
            yield NextEventSC(operation_id=operation_id, payload=data.formatted)

    except GraphQLError as error:
        result = get_error_execution_result(error)
        yield NextEventSC(operation_id=operation_id, payload=result.formatted)

    except GraphQLErrorGroup as error:
        result = get_error_execution_result(error)
        yield NextEventSC(operation_id=operation_id, payload=result.formatted)

    except Exception as error:  # noqa: BLE001
        result = get_error_execution_result(GraphQLUnexpectedError(message=str(error)))
        yield NextEventSC(operation_id=operation_id, payload=result.formatted)

    yield CompletedEventSC(operation_id=operation_id)


def get_sse_stream_token_key() -> str:
    return f"{undine_settings.SSE_STREAM_SESSION_PREFIX}|token"


def get_sse_stream_state_key() -> str:
    return f"{undine_settings.SSE_STREAM_SESSION_PREFIX}|state"


def get_sse_operation_key(*, operation_id: str) -> str:
    return f"{undine_settings.SSE_STREAM_SESSION_PREFIX}|operation|{operation_id}"


def get_sse_stream_claim_key(stream_token: str) -> str:
    return f"{undine_settings.SSE_STREAM_SESSION_PREFIX}|stream-claim|{stream_token}"


def get_sse_operation_claim_key(stream_token: str, operation_id: str) -> str:
    return f"{undine_settings.SSE_STREAM_SESSION_PREFIX}|operation-claim|{stream_token}|{operation_id}"


@dataclasses.dataclass(slots=True, kw_only=True)
class SSESessionStore:
    """Manages SSE stream state in Django sessions."""

    session: SessionBase

    async def refresh(self) -> None:
        """Force load of the session data from the session store."""
        # Django 5.0 compat: SessionBase.aload was added in Django 5.1.
        if hasattr(self.session, "aload"):
            self.session._session_cache = await self.session.aload()  # noqa: SLF001
        else:
            self.session._session_cache = await sync_to_async(self.session.load)()  # noqa: SLF001

    async def save(self) -> None:
        # Django 5.0 compat: SessionBase.asave was added in Django 5.1.
        if hasattr(self.session, "asave"):
            await self.session.asave()
        else:
            await sync_to_async(self.session.save)()

    # Stream token

    def get_stream_token(self) -> str | None:
        return self.session.get(get_sse_stream_token_key())

    def set_stream_token(self, stream_token: str) -> None:
        self.session[get_sse_stream_token_key()] = stream_token

    def delete_stream_token(self) -> None:
        self.session.pop(get_sse_stream_token_key(), None)

    # Stream state

    def get_stream_state(self) -> SSEState | None:
        return self.session.get(get_sse_stream_state_key())

    def set_stream_state(self, state: SSEState) -> None:
        self.session[get_sse_stream_state_key()] = state.value

    def delete_stream_state(self) -> None:
        self.session.pop(get_sse_stream_state_key(), None)

    # Operations

    def has_operation(self, operation_id: str) -> bool:
        return get_sse_operation_key(operation_id=operation_id) in self.session

    def set_operation(self, operation_id: str) -> None:
        key = get_sse_operation_key(operation_id=operation_id)
        self.session[key] = operation_id

    def delete_operation(self, operation_id: str) -> None:
        self.session.pop(get_sse_operation_key(operation_id=operation_id), None)

    def delete_all_operations(self) -> None:
        prefix = get_sse_operation_key(operation_id="")
        for key in list(self.session.keys()):
            if key.startswith(prefix):
                self.session.pop(key, None)


@dataclasses.dataclass(slots=True, kw_only=True)
class SSEClaimStore:
    """Manages cache-based claims for SSE stream and operation concurrency control."""

    claim_timeout: int = 30

    @property
    def cache(self) -> Any:
        return caches[django_settings.SESSION_CACHE_ALIAS]

    async def claim_stream(self, stream_token: str) -> bool:
        key = get_sse_stream_claim_key(stream_token)
        return await self.cache.aadd(key, "1", timeout=self.claim_timeout)

    async def release_stream_claim(self, stream_token: str) -> None:
        key = get_sse_stream_claim_key(stream_token)
        await self.cache.adelete(key)

    async def claim_operation(self, stream_token: str, operation_id: str) -> bool:
        key = get_sse_operation_claim_key(stream_token, operation_id)
        return await self.cache.aadd(key, "1", timeout=self.claim_timeout)

    async def release_operation_claim(self, stream_token: str, operation_id: str) -> None:
        key = get_sse_operation_claim_key(stream_token, operation_id)
        await self.cache.adelete(key)


@dataclasses.dataclass(kw_only=True, slots=True)
class GraphQLOverSSESCHandler:
    """Handler for the GraphQL over SSE Single Connection protocol."""

    signaler: SSESignaler
    session: SSESessionStore
    claims: SSEClaimStore

    def create_new_session_token(self) -> str:
        return uuid.uuid4().hex

    async def reserve_stream(self) -> str:
        await self.session.refresh()

        existing_token = self.session.get_stream_token()
        existing_state = self.session.get_stream_state()

        if existing_token is not None:
            if existing_state == SSEState.OPENED:
                await self.signaler.signal_stream_close(existing_token)
            self.session.delete_all_operations()

        stream_token = self.create_new_session_token()

        self.session.set_stream_token(stream_token)
        self.session.set_stream_state(SSEState.REGISTERED)
        await self.session.save()

        return stream_token

    async def open_event_stream(self, stream_token: str) -> None:
        await self.session.refresh()

        if self.session.get_stream_token() != stream_token:
            raise GraphQLSSEStreamNotFoundError

        if self.session.get_stream_state() == SSEState.OPENED:
            raise GraphQLSSEStreamAlreadyOpenError

        claimed = await self.claims.claim_stream(stream_token)
        if not claimed:
            raise GraphQLSSEStreamAlreadyOpenError

        await self.signaler.register_stream(stream_token)
        await self.signaler.signal_stream_open(stream_token)

        self.session.set_stream_state(SSEState.OPENED)
        await self.session.save()

        await self.claims.release_stream_claim(stream_token)

    async def start_operation(self, stream_token: str, operation_id: str) -> bool:
        stream_opened: bool = False

        await self.signaler.register_stream_open(stream_token)

        await self.session.refresh()

        if self.session.get_stream_token() != stream_token:
            raise GraphQLSSEStreamNotFoundError

        if self.session.get_stream_state() == SSEState.OPENED:
            stream_opened = True

        if self.session.has_operation(operation_id):
            raise GraphQLSSEOperationAlreadyExistsError

        claimed = await self.claims.claim_operation(stream_token, operation_id)
        if not claimed:
            raise GraphQLSSEOperationAlreadyExistsError

        self.session.set_operation(operation_id)
        await self.session.save()

        await self.claims.release_operation_claim(stream_token, operation_id)

        await self.signaler.register_operation(stream_token, operation_id)

        return stream_opened

    async def execute_operation(
        self,
        stream_token: str,
        operation_id: str,
        params: GraphQLHttpParams,
        request: DjangoRequestProtocol,
    ) -> None:
        completed: bool = False
        try:
            async for event in execute_graphql_sse_sc(operation_id, params, request):
                completed = completed or event.event == "complete"
                await self.signaler.signal_operation_event(stream_token, event.encode())

        # Catch any exception so to make sure client receives a complete event.
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            if not completed:
                # Suppress errors in case it's the signaler that's dead.
                with suppress(Exception):
                    complete_event = CompletedEventSC(operation_id=operation_id)
                    await self.signaler.signal_operation_event(stream_token, complete_event.encode())

    async def finalize_operation(self, stream_token: str, operation_id: str) -> None:
        await self.signaler.unregister_operation(stream_token, operation_id)

        await self.session.refresh()
        if self.session.get_stream_token() == stream_token:
            self.session.delete_operation(operation_id)
            await self.session.save()

    async def cancel_operation(self, stream_token: str, operation_id: str) -> None:
        await self.session.refresh()

        if self.session.get_stream_token() != stream_token:
            raise GraphQLSSEStreamNotFoundError

        await self.signaler.signal_operation_cancel(stream_token, operation_id)

    async def disconnect_stream(self, stream_token: str) -> None:
        await self.signaler.signal_operation_cancel_all(stream_token)
        await self.signaler.unregister_stream(stream_token)

        await self.session.refresh()
        if self.session.get_stream_token() == stream_token:
            self.session.delete_all_operations()
            self.session.delete_stream_token()
            self.session.delete_stream_state()
            await self.session.save()

    async def disconnect_operation(self, stream_token: str) -> None:
        await self.signaler.unregister_stream_open(stream_token)


@dataclasses.dataclass(kw_only=True)  # No slots due to '@cached_property'
class SSERequest:
    """
    Wraps the received HTTP events as a Django request.
    Importantly, this makes the middleware properties set by common middlewares available.
    """

    scope: HTTPASGIScope
    messages: list[HTTPRequestEvent]

    @cached_property
    def _request(self) -> ASGIRequest:
        body = b"".join(message["body"] for message in self.messages if "body" in message)
        return ASGIRequest(scope=self.scope, body_file=io.BytesIO(body))

    @property
    def GET(self) -> QueryDict:  # noqa: N802
        return self._request.GET

    @property
    def POST(self) -> QueryDict:  # noqa: N802
        return self._request.POST

    @property
    def COOKIES(self) -> dict[str, str]:  # noqa: N802
        return self._request.COOKIES

    @property
    def FILES(self) -> MultiValueDict[str, UploadedFile]:  # noqa: N802
        return self._request.FILES

    @property
    def META(self) -> dict[str, Any]:  # noqa: N802
        return self._request.META

    @property
    def scheme(self) -> str | None:
        return self._request.scheme

    @property
    def path(self) -> str:
        return self._request.path

    @property
    def method(self) -> RequestMethod:
        return self._request.method  # type: ignore[return-value]

    @property
    def headers(self) -> HttpHeaders:
        return self._request.headers

    @property
    def body(self) -> bytes:
        return self._request.body

    @property
    def encoding(self) -> str | None:
        return self._request.encoding

    @property
    def user(self) -> User | AnonymousUser:
        return self.scope["user"]

    async def auser(self) -> User | AnonymousUser:
        return self.user

    @property
    def session(self) -> SessionBase:
        return self.scope["session"]

    @property
    def content_type(self) -> str | None:
        return self._request.content_type

    @property
    def content_params(self) -> dict[str, str] | None:
        return self._request.content_params

    @property
    def accepted_types(self) -> list[MediaType]:
        return self._request.accepted_types

    @property
    def response_content_type(self) -> str:
        return getattr(self, "_response_content_type", "application/json")

    @response_content_type.setter
    def response_content_type(self, value: str) -> None:
        self._response_content_type = value
