from __future__ import annotations

import asyncio

import pytest

from tests.test_integrations.test_channels.helpers import _create_session, _create_user, _open_stream, _reserve_stream

pytestmark = [
    pytest.mark.django_db(transaction=True),
]


async def test_channels__sse__keep_alive_ping(undine_settings) -> None:
    undine_settings.SSE_KEEP_ALIVE_INTERVAL = 0.1  # type: ignore[assignment]

    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    communicator = await _open_stream(user, session, token)

    # Wait for the first periodic keep-alive ping
    ping = await communicator.receive_output(timeout=3)
    assert ping["type"] == "http.response.body"
    assert ping["body"] == b":\n\n"
    assert ping.get("more_body") is True


async def test_channels__sse__keep_alive_ping__disabled(undine_settings) -> None:
    undine_settings.SSE_KEEP_ALIVE_INTERVAL = 0

    user = await _create_user()
    session = await _create_session(user)
    token = await _reserve_stream(user, session)
    communicator = await _open_stream(user, session, token)

    # No periodic ping should arrive
    with pytest.raises(asyncio.TimeoutError):
        await communicator.receive_output(timeout=0.01)
