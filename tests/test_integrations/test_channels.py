from __future__ import annotations

import json
import uuid
from http import HTTPStatus

import pytest
from django.contrib.auth.models import AnonymousUser

from tests.test_integrations.helpers import (
    _create_session,
    _create_user,
    _open_stream,
    _reserve_stream,
    get_router,
    make_scope,
    make_sse_communicator,
    sse_get_response,
    sse_send_request,
)
from undine import Entrypoint, RootType, create_schema
from undine.typing import PingMessage, PongMessage, SSEState

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.django_db(transaction=True),
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


# SSE - Reserve Stream


async def test_channels__sse__reserve_stream(undine_settings) -> None:
    user = await _create_user()
    session = await _create_session(user)

    communicator = make_sse_communicator(
        method="PUT",
        headers=[(b"accept", b"text/plain")],
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.CREATED
    assert uuid.UUID(response["body"])

    # Verify session was updated
    session_key = undine_settings.SSE_STREAM_SESSION_KEY
    stream_state = await session.aget(session_key)
    assert stream_state is not None
    assert stream_state["state"] == SSEState.REGISTERED
    assert stream_state["stream_token"] == response["body"]


async def test_channels__sse__reserve_stream__unauthenticated() -> None:
    session = await _create_session()

    communicator = make_sse_communicator(
        method="PUT",
        headers=[(b"accept", b"text/plain")],
        user=AnonymousUser(),
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.UNAUTHORIZED
    assert response["json"]["errors"][0]["message"] == (
        "GraphQL over SSE requires authentication in single connection mode"
    )


async def test_channels__sse__reserve_stream__already_reserved() -> None:
    user = await _create_user()
    session = await _create_session(user)

    # Reserve first
    await _reserve_stream(user, session)

    # Try to reserve again
    communicator = make_sse_communicator(
        method="PUT",
        headers=[(b"accept", b"text/plain")],
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.CONFLICT
    assert response["json"]["errors"][0]["message"] == "Stream already registered"


# SSE - Get Stream


async def test_channels__sse__get_stream(undine_settings) -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)

    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=f"token={token}".encode(),
        user=user,
        session=session,
    )
    await sse_send_request(communicator)

    start = await communicator.receive_output(timeout=3)
    assert start["type"] == "http.response.start"
    assert start["status"] == HTTPStatus.OK

    headers = {k.decode(): v.decode() for k, v in start.get("headers", [])}
    assert "text/event-stream" in headers.get("Content-Type", "")

    # First body event (empty, keeps connection open)
    body_event = await communicator.receive_output(timeout=3)
    assert body_event["type"] == "http.response.body"
    assert body_event.get("more_body") is True

    # Verify session was updated
    session_key = undine_settings.SSE_STREAM_SESSION_KEY
    stream_state = await session.aget(session_key)
    assert stream_state is not None
    assert stream_state["state"] == SSEState.OPENED


async def test_channels__sse__get_stream__unauthenticated() -> None:
    session = await _create_session()

    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=b"token=some-token",
        user=AnonymousUser(),
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.UNAUTHORIZED
    assert response["json"]["errors"][0]["message"] == (
        "GraphQL over SSE requires authentication in single connection mode"
    )


async def test_channels__sse__get_stream__already_open() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)

    # Open stream first
    await _open_stream(user, session, token)

    # Try to open again
    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=f"token={token}".encode(),
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.CONFLICT
    assert response["json"]["errors"][0]["message"] == "Stream already open"


async def test_channels__sse__get_stream__stream_not_registered() -> None:
    user = await _create_user()
    session = await _create_session(user)

    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=b"token=nonexistent-token",
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.NOT_FOUND
    assert response["json"]["errors"][0]["message"] == "Stream not found"


async def test_channels__sse__get_stream__wrong_stream_token() -> None:
    user = await _create_user()
    session = await _create_session(user)

    # Reserve stream, but try to open with wrong token
    await _reserve_stream(user, session)

    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        query_string=b"token=wrong-token",
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.NOT_FOUND
    assert response["json"]["errors"][0]["message"] == "Stream not found"


async def test_channels__sse__get_stream__stream_token_missing() -> None:
    user = await _create_user()
    session = await _create_session(user)
    await _reserve_stream(user, session)

    communicator = make_sse_communicator(
        method="GET",
        headers=[(b"accept", b"text/event-stream")],
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.BAD_REQUEST
    assert response["json"]["errors"][0]["message"] == "Stream token missing"


# SSE - Subscribe


async def test_channels__sse__subscribe(undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_SSE = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    undine_settings.SCHEMA = create_schema(query=Query)

    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    body = json.dumps({
        "query": "query { test }",
        "extensions": {"operationId": "op-1"},
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", token.encode()),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.ACCEPTED


async def test_channels__sse__subscribe__unauthenticated() -> None:
    session = await _create_session()

    body = json.dumps({
        "query": "subscription { test }",
        "extensions": {"operationId": "op-1"},
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", b"some-token"),
        ],
        user=AnonymousUser(),
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.UNAUTHORIZED
    assert response["json"]["errors"][0]["message"] == (
        "GraphQL over SSE requires authentication in single connection mode"
    )


async def test_channels__sse__subscribe__stream_not_registered() -> None:
    user = await _create_user()
    session = await _create_session(user)

    body = json.dumps({
        "query": "subscription { test }",
        "extensions": {"operationId": "op-1"},
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", b"nonexistent-token"),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.NOT_FOUND
    assert response["json"]["errors"][0]["message"] == "Stream not found"


async def test_channels__sse__subscribe__stream_not_opened() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)

    body = json.dumps({
        "query": "subscription { test }",
        "extensions": {"operationId": "op-1"},
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", token.encode()),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.NOT_FOUND
    assert response["json"]["errors"][0]["message"] == "Stream not found"


async def test_channels__sse__subscribe__wrong_stream_token() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    body = json.dumps({
        "query": "subscription { test }",
        "extensions": {"operationId": "op-1"},
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", b"wrong-token"),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.NOT_FOUND
    assert response["json"]["errors"][0]["message"] == "Stream not found"


async def test_channels__sse__subscribe__stream_token_missing() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    body = json.dumps({
        "query": "subscription { test }",
        "extensions": {"operationId": "op-1"},
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.BAD_REQUEST
    assert response["json"]["errors"][0]["message"] == "Stream token missing"


async def test_channels__sse__subscribe__operation_id_missing() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    body = json.dumps({
        "query": "subscription { test }",
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", token.encode()),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.BAD_REQUEST
    assert response["json"]["errors"][0]["message"] == "Operation ID is missing"


async def test_channels__sse__subscribe__operation_already_exists(undine_settings) -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    operation_id = "op-1"

    # Mark operation as already existing in session
    session_key = undine_settings.SSE_STREAM_SESSION_KEY
    operation_key = f"{session_key}|{operation_id}"
    await session.aset(key=operation_key, value=True)
    await session.asave()

    body = json.dumps({
        "query": "subscription { test }",
        "extensions": {"operationId": operation_id},
    }).encode()

    communicator = make_sse_communicator(
        method="POST",
        headers=[
            (b"accept", b"application/json"),
            (b"content-type", b"application/json"),
            (b"x-graphql-event-stream-token", token.encode()),
        ],
        user=user,
        session=session,
    )
    await sse_send_request(communicator, body=body)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.CONFLICT
    assert response["json"]["errors"][0]["message"] == "Operation with ID already exists"


# SSE - Cancel Subscription


async def test_channels__sse__cancel_subscription() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    communicator = make_sse_communicator(
        method="DELETE",
        headers=[(b"x-graphql-event-stream-token", token.encode())],
        query_string=b"operationId=op-1",
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.OK


async def test_channels__sse__cancel_subscription__unauthenticated() -> None:
    session = await _create_session()

    communicator = make_sse_communicator(
        method="DELETE",
        headers=[(b"x-graphql-event-stream-token", b"some-token")],
        query_string=b"operationId=op-1",
        user=AnonymousUser(),
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.UNAUTHORIZED
    assert response["json"]["errors"][0]["message"] == (
        "GraphQL over SSE requires authentication in single connection mode"
    )


async def test_channels__sse__cancel_subscription__operation_id_missing() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    communicator = make_sse_communicator(
        method="DELETE",
        headers=[(b"x-graphql-event-stream-token", token.encode())],
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.BAD_REQUEST
    assert response["json"]["errors"][0]["message"] == "Operation ID is missing"


async def test_channels__sse__cancel_subscription__operation_not_found() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    communicator = make_sse_communicator(
        method="DELETE",
        headers=[(b"x-graphql-event-stream-token", token.encode())],
        query_string=b"operationId=nonexistent",
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    # cancel_operation sends to the group but there's no consumer listening,
    # so it just succeeds silently
    assert response["status"] == HTTPStatus.OK


async def test_channels__sse__cancel_subscription__stream_not_registered() -> None:
    user = await _create_user()
    session = await _create_session(user)

    communicator = make_sse_communicator(
        method="DELETE",
        headers=[(b"x-graphql-event-stream-token", b"nonexistent-token")],
        query_string=b"operationId=op-1",
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.NOT_FOUND
    assert response["json"]["errors"][0]["message"] == "Stream not found"


async def test_channels__sse__cancel_subscription__stream_not_opened() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)

    communicator = make_sse_communicator(
        method="DELETE",
        headers=[(b"x-graphql-event-stream-token", token.encode())],
        query_string=b"operationId=op-1",
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.NOT_FOUND
    assert response["json"]["errors"][0]["message"] == "Stream not found"


async def test_channels__sse__cancel_subscription__wrong_stream_token() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    communicator = make_sse_communicator(
        method="DELETE",
        headers=[(b"x-graphql-event-stream-token", b"wrong-token")],
        query_string=b"operationId=op-1",
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.NOT_FOUND
    assert response["json"]["errors"][0]["message"] == "Stream not found"


async def test_channels__sse__cancel_subscription__stream_token_missing() -> None:
    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    await _open_stream(user, session, token)

    communicator = make_sse_communicator(
        method="DELETE",
        query_string=b"operationId=op-1",
        user=user,
        session=session,
    )
    await sse_send_request(communicator)
    response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.BAD_REQUEST
    assert response["json"]["errors"][0]["message"] == "Stream token missing"


# SSE Router


async def test_channels__sse_router__non_graphql_path_routes_to_asgi(undine_settings) -> None:
    undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1 = False

    router = get_router()
    scope = make_scope(path="/other/")

    await router(scope, None, None)

    router.asgi_application.assert_awaited_once()
    router.sse_application.assert_not_awaited()


async def test_channels__sse_router__http2_routes_to_asgi(undine_settings) -> None:
    undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1 = False

    router = get_router()
    scope = make_scope(http_version="2.0")

    await router(scope, None, None)

    router.asgi_application.assert_awaited_once()
    router.sse_application.assert_not_awaited()


async def test_channels__sse_router__distinct_connections_setting_routes_to_asgi(undine_settings) -> None:
    undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1 = True

    router = get_router()
    scope = make_scope()

    await router(scope, None, None)

    router.asgi_application.assert_awaited_once()
    router.sse_application.assert_not_awaited()


async def test_channels__sse_router__put_routes_to_sse(undine_settings) -> None:
    undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1 = False

    router = get_router()
    scope = make_scope(method="PUT")

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.asgi_application.assert_not_awaited()


async def test_channels__sse_router__delete_routes_to_sse(undine_settings) -> None:
    undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1 = False

    router = get_router()
    scope = make_scope(method="DELETE")

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.asgi_application.assert_not_awaited()


async def test_channels__sse_router__get_with_token_query_param_routes_to_sse(undine_settings) -> None:
    undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1 = False

    router = get_router()
    scope = make_scope(method="GET", query_string=b"token=some-token")

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.asgi_application.assert_not_awaited()


async def test_channels__sse_router__get_with_token_header_routes_to_sse(undine_settings) -> None:
    undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1 = False

    router = get_router()
    scope = make_scope(
        method="GET",
        headers=[(b"x-graphql-event-stream-token", b"some-token")],
    )

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.asgi_application.assert_not_awaited()


async def test_channels__sse_router__post_with_token_query_param_routes_to_sse(undine_settings) -> None:
    undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1 = False

    router = get_router()
    scope = make_scope(method="POST", query_string=b"token=some-token")

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.asgi_application.assert_not_awaited()


async def test_channels__sse_router__post_with_token_header_routes_to_sse(undine_settings) -> None:
    undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1 = False

    router = get_router()
    scope = make_scope(
        method="POST",
        headers=[(b"x-graphql-event-stream-token", b"some-token")],
    )

    await router(scope, None, None)

    router.sse_application.assert_awaited_once()
    router.asgi_application.assert_not_awaited()


async def test_channels__sse_router__get_without_token_routes_to_asgi(undine_settings) -> None:
    undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1 = False

    router = get_router()
    scope = make_scope(method="GET")

    await router(scope, None, None)

    router.asgi_application.assert_awaited_once()
    router.sse_application.assert_not_awaited()


async def test_channels__sse_router__post_without_token_routes_to_asgi(undine_settings) -> None:
    undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1 = False

    router = get_router()
    scope = make_scope(method="POST")

    await router(scope, None, None)

    router.asgi_application.assert_awaited_once()
    router.sse_application.assert_not_awaited()
