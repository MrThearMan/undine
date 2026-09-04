from __future__ import annotations

from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import pytest
from asgiref.typing import HTTPRequestEvent
from channels.exceptions import StopConsumer
from django.contrib.auth.models import AnonymousUser
from graphql import GraphQLError

from tests.helpers import exact
from tests.test_integrations.test_channels.helpers import (
    _create_session,
    _create_user,
    make_http_scope,
    make_sse_communicator,
    sse_get_response,
    sse_send_request,
)
from undine.exceptions import ChannelLayerMissingError, GraphQLErrorGroup
from undine.integrations.channels import SSEStreamReservationConsumer

pytestmark = [
    pytest.mark.django_db(transaction=True),
]


async def test_channels__sse_consumer__no_channel_layer() -> None:
    consumer = SSEStreamReservationConsumer()

    scope = make_http_scope(method="PUT")
    scope["session"] = None  # type: ignore[typeddict-unknown-key]

    message = "No channel layer has been configured for the alias 'default'"

    with (
        patch("undine.integrations.channels.get_channel_layer", return_value=None),
        pytest.raises(ChannelLayerMissingError, match=exact(message)),
    ):
        await consumer(scope, None, None)  # type: ignore[arg-type]


async def test_channels__sse_consumer__chunked_body_request() -> None:
    user = await _create_user()
    session = await _create_session(user)

    # First, reserve a stream normally to get the session into a known state
    communicator = make_sse_communicator(
        method="PUT",
        headers=[(b"accept", b"text/plain")],
        user=user,
        session=session,
    )

    # Send body with more_body=True first (partial chunk), then False to complete
    await communicator.send_input(HTTPRequestEvent(type="http.request", body=b"", more_body=True))
    # The consumer is waiting for more body -> send the final chunk
    await communicator.send_input(HTTPRequestEvent(type="http.request", body=b"", more_body=False))

    response = await sse_get_response(communicator)
    assert response["status"] == HTTPStatus.CREATED


async def test_channels__sse_consumer__unexpected_exception_in_handler() -> None:
    user = await _create_user()
    session = await _create_session(user)

    communicator = make_sse_communicator(
        method="PUT",
        headers=[(b"accept", b"text/plain")],
        user=user,
        session=session,
    )

    with patch(
        "undine.integrations.channels.SSEStreamReservationConsumer.handle",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        await sse_send_request(communicator)
        response = await sse_get_response(communicator)

    assert response["status"] == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response["json"]["errors"] == [{"message": "Unexpected error.", "extensions": {"status_code": 500}}]


async def test_channels__sse_consumer__graphql_error_group_response() -> None:
    user = await _create_user()
    session = await _create_session(user)

    communicator = make_sse_communicator(
        method="PUT",
        headers=[(b"accept", b"text/plain")],
        user=user,
        session=session,
    )

    error_group = GraphQLErrorGroup([GraphQLError("err1"), GraphQLError("err2")])

    with patch(
        "undine.integrations.channels.SSEStreamReservationConsumer.handle",
        new=AsyncMock(side_effect=error_group),
    ):
        await sse_send_request(communicator)
        response = await sse_get_response(communicator)

    # GraphQLErrorGroup has no extensions.status_code so defaults to 500
    assert response["status"] == HTTPStatus.INTERNAL_SERVER_ERROR


async def test_channels__sse_consumer__http_request__raises_stop_consumer_when_unauthenticated() -> None:
    consumer = SSEStreamReservationConsumer()
    consumer.scope = make_http_scope(user=AnonymousUser())  # type: ignore[arg-type]
    consumer.base_send = AsyncMock()

    message = HTTPRequestEvent(type="http.request", body=b"", more_body=False)
    with pytest.raises(StopConsumer):
        await consumer.http_request(message)
