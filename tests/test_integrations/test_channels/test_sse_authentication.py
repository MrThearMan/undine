from __future__ import annotations

from http import HTTPStatus

import pytest
from django.contrib.auth.models import AnonymousUser

from tests.test_integrations.test_channels.helpers import (
    _create_session,
    make_sse_communicator,
    session_aget,
    sse_get_response,
    sse_send_request,
)
from undine.utils.graphql.server_sent_events import get_sse_stream_state_key, get_sse_stream_token_key

pytestmark = [
    pytest.mark.django_db(transaction=True),
]


async def test_channels__sse__consumer_stopped_when_unauthenticated() -> None:
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

    # handle() was never called — session remains untouched
    assert await session_aget(session, get_sse_stream_token_key()) is None
    assert await session_aget(session, get_sse_stream_state_key()) is None
