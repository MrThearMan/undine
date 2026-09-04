from __future__ import annotations

import pytest
from django.http import HttpResponse

from tests.test_integrations.test_channels.helpers import get_graphql_sse_operation_router, make_http_scope
from undine.http.responses import HttpMethodNotAllowedResponse, HttpUnsupportedContentTypeResponse
from undine.integrations.channels import GraphQLSSEOperationRouter
from undine.typing import RequestMethod

pytestmark = [
    pytest.mark.django_db(transaction=True),
]


@pytest.mark.parametrize("method", ["HEAD", "PATCH", "OPTIONS"])
async def test_channels__sse_operation_router__non_accepted_method(undine_settings, method) -> None:
    router = get_graphql_sse_operation_router()
    scope = make_http_scope(method=method)

    await router(scope, None, None)

    router.send_http_response.assert_awaited_once()
    router.stream_reservation_consumer.assert_not_awaited()
    router.event_stream_consumer.assert_not_awaited()
    router.operation_consumer.assert_not_awaited()
    router.operation_cancellation_consumer.assert_not_awaited()

    response = router.send_http_response.await_args.kwargs["response"]
    assert isinstance(response, HttpMethodNotAllowedResponse)


async def test_channels__sse_operation_router__stream_reservation(undine_settings) -> None:
    router = get_graphql_sse_operation_router()
    scope = make_http_scope(method="PUT", headers=[(b"accept", b"text/plain")])

    await router(scope, None, None)

    router.send_http_response.assert_not_awaited()
    router.stream_reservation_consumer.assert_awaited_once()
    router.event_stream_consumer.assert_not_awaited()
    router.operation_consumer.assert_not_awaited()
    router.operation_cancellation_consumer.assert_not_awaited()


async def test_channels__sse_operation_router__stream_reservation__doesnt_accept_test_plain(undine_settings) -> None:
    router = get_graphql_sse_operation_router()
    scope = make_http_scope(method="PUT", headers=[(b"accept", b"application/json")])

    await router(scope, None, None)

    router.send_http_response.assert_awaited_once()
    router.stream_reservation_consumer.assert_not_awaited()
    router.event_stream_consumer.assert_not_awaited()
    router.operation_consumer.assert_not_awaited()
    router.operation_cancellation_consumer.assert_not_awaited()

    response = router.send_http_response.await_args.kwargs["response"]
    assert isinstance(response, HttpUnsupportedContentTypeResponse)


@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_channels__sse_operation_router__event_stream(method: RequestMethod) -> None:
    router = get_graphql_sse_operation_router()
    scope = make_http_scope(method=method, headers=[(b"accept", b"text/event-stream")])

    await router(scope, None, None)

    router.send_http_response.assert_not_awaited()
    router.stream_reservation_consumer.assert_not_awaited()
    router.event_stream_consumer.assert_awaited_once()
    router.operation_consumer.assert_not_awaited()
    router.operation_cancellation_consumer.assert_not_awaited()


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize("accept", [b"application/json", b"application/*", b"*/*"])
async def test_channels__sse_operation_router__operation(method: RequestMethod, accept: bytes) -> None:
    router = get_graphql_sse_operation_router()
    scope = make_http_scope(method=method, headers=[(b"accept", accept)])

    await router(scope, None, None)

    router.send_http_response.assert_not_awaited()
    router.stream_reservation_consumer.assert_not_awaited()
    router.event_stream_consumer.assert_not_awaited()
    router.operation_consumer.assert_awaited_once()
    router.operation_cancellation_consumer.assert_not_awaited()


@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_channels__sse_operation_router__operation__cannot_accept_json(method: RequestMethod) -> None:
    router = get_graphql_sse_operation_router()
    scope = make_http_scope(method=method, headers=[(b"accept", b"text/html")])

    await router(scope, None, None)

    router.send_http_response.assert_awaited_once()
    router.stream_reservation_consumer.assert_not_awaited()
    router.event_stream_consumer.assert_not_awaited()
    router.operation_consumer.assert_not_awaited()
    router.operation_cancellation_consumer.assert_not_awaited()

    response = router.send_http_response.await_args.kwargs["response"]
    assert isinstance(response, HttpUnsupportedContentTypeResponse)


async def test_channels__sse_operation_router__cancellation(undine_settings) -> None:
    router = get_graphql_sse_operation_router()
    scope = make_http_scope(method="DELETE")

    await router(scope, None, None)

    router.send_http_response.assert_not_awaited()
    router.stream_reservation_consumer.assert_not_awaited()
    router.event_stream_consumer.assert_not_awaited()
    router.operation_consumer.assert_not_awaited()
    router.operation_cancellation_consumer.assert_awaited_once()


async def test_channels__sse_operation_router__send_http_response_static() -> None:
    events = []

    async def mock_send(event: dict) -> None:  # noqa: RUF029
        events.append(event)

    response = HttpResponse(content=b"hello", status=200, content_type="text/plain")
    await GraphQLSSEOperationRouter.send_http_response(mock_send, response=response)

    assert len(events) == 2
    assert events[0]["type"] == "http.response.start"
    assert events[0]["status"] == 200

    assert events[1]["type"] == "http.response.body"
    assert events[1]["body"] == b"hello"
    assert events[1]["more_body"] is False
