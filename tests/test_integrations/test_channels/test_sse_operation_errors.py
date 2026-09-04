from __future__ import annotations

import asyncio

import pytest
from graphql import GraphQLError

from tests.helpers import TEST_WAIT_TIME
from tests.test_integrations.test_channels.helpers import (
    create_failing_subscription_schema,
    create_mutation_schema,
    create_query_schema,
    open_sse_stream,
    read_sse_complete_event,
    read_sse_next_event,
    session_aget,
    session_aload,
    submit_sse_operation,
)
from undine.exceptions import GraphQLErrorGroup
from undine.utils.graphql.server_sent_events import get_sse_operation_key

pytestmark = [
    pytest.mark.django_db(transaction=True),
]


async def test_channels__sse__validation_error_on_submit(undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_SSE = True
    undine_settings.SCHEMA = create_query_schema()

    stream = await open_sse_stream()
    operation_id = "op-invalid"
    await submit_sse_operation(stream, query="query { nonExistentField }", operation_id=operation_id)

    payload = await read_sse_next_event(stream, operation_id=operation_id)
    assert "errors" in payload

    await read_sse_complete_event(stream, operation_id=operation_id)

    await asyncio.sleep(TEST_WAIT_TIME)


async def test_channels__sse__query_rejected_when_not_allowed(undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_SSE = False
    undine_settings.SCHEMA = create_query_schema()

    stream = await open_sse_stream()
    operation_id = "op-no-query"
    await submit_sse_operation(stream, query="query { test }", operation_id=operation_id)

    payload = await read_sse_next_event(stream, operation_id=operation_id)
    assert "Cannot use Server-Sent Events for queries" in payload["errors"][0]["message"]

    await read_sse_complete_event(stream, operation_id=operation_id)

    await asyncio.sleep(TEST_WAIT_TIME)


async def test_channels__sse__mutation_rejected_when_not_allowed(undine_settings) -> None:
    undine_settings.ALLOW_MUTATIONS_WITH_SSE = False
    undine_settings.SCHEMA = create_mutation_schema()

    stream = await open_sse_stream()
    operation_id = "op-no-mutation"
    await submit_sse_operation(stream, query="mutation { doSomething }", operation_id=operation_id)

    payload = await read_sse_next_event(stream, operation_id=operation_id)
    assert "Cannot use Server-Sent Events for mutations" in payload["errors"][0]["message"]

    await read_sse_complete_event(stream, operation_id=operation_id)

    await asyncio.sleep(TEST_WAIT_TIME)


async def test_channels__sse__complete_event_on_unexpected_error(undine_settings) -> None:
    undine_settings.SCHEMA = create_failing_subscription_schema(RuntimeError("unexpected failure"))

    stream = await open_sse_stream()
    operation_id = "op-err"
    await submit_sse_operation(stream, query="subscription { errorStream }", operation_id=operation_id)

    first_payload = await read_sse_next_event(stream, operation_id=operation_id)
    assert first_payload == {"data": {"errorStream": "first"}}

    error_payload = await read_sse_next_event(stream, operation_id=operation_id)
    assert "errors" in error_payload

    await read_sse_complete_event(stream, operation_id=operation_id)

    await asyncio.sleep(TEST_WAIT_TIME)
    await session_aload(stream.session)
    assert await session_aget(stream.session, get_sse_operation_key(operation_id=operation_id)) is None


async def test_channels__sse__graphql_error_during_subscription(undine_settings) -> None:
    undine_settings.SCHEMA = create_failing_subscription_schema(GraphQLError("subscription failed"))

    stream = await open_sse_stream()
    operation_id = "op-gql-err"
    await submit_sse_operation(stream, query="subscription { errorStream }", operation_id=operation_id)

    first_payload = await read_sse_next_event(stream, operation_id=operation_id)
    assert first_payload == {"data": {"errorStream": "first"}}

    error_payload = await read_sse_next_event(stream, operation_id=operation_id)
    assert error_payload["errors"][0]["message"] == "subscription failed"

    await read_sse_complete_event(stream, operation_id=operation_id)

    await asyncio.sleep(TEST_WAIT_TIME)
    await session_aload(stream.session)
    assert await session_aget(stream.session, get_sse_operation_key(operation_id=operation_id)) is None


async def test_channels__sse__graphql_error_group_during_subscription(undine_settings) -> None:
    error_group = GraphQLErrorGroup([GraphQLError("error one"), GraphQLError("error two")])
    undine_settings.SCHEMA = create_failing_subscription_schema(error_group)

    stream = await open_sse_stream()
    operation_id = "op-gql-errgroup"
    await submit_sse_operation(stream, query="subscription { errorStream }", operation_id=operation_id)

    first_payload = await read_sse_next_event(stream, operation_id=operation_id)
    assert first_payload == {"data": {"errorStream": "first"}}

    error_payload = await read_sse_next_event(stream, operation_id=operation_id)
    error_messages = [error["message"] for error in error_payload["errors"]]
    assert error_messages == ["error one", "error two"]

    await read_sse_complete_event(stream, operation_id=operation_id)

    await asyncio.sleep(TEST_WAIT_TIME)
    await session_aload(stream.session)
    assert await session_aget(stream.session, get_sse_operation_key(operation_id=operation_id)) is None
