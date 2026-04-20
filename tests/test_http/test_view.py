from __future__ import annotations

import asyncio
import json
import sys
import types
import urllib.parse
from inspect import iscoroutine
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from django.http import HttpResponse, StreamingHttpResponse
from django.http.request import MediaType, QueryDict
from django.urls import reverse
from graphql import GraphQLError, GraphQLField, GraphQLObjectType, GraphQLSchema, GraphQLString

from tests.helpers import MockRequest, create_multipart_form_data_request
from undine.http.content_negotiation import add_media_type_param
from undine.http.responses import (
    HttpEventSourcingNotAllowedResponse,
    HttpMethodNotAllowedResponse,
    HttpUnsupportedContentTypeResponse,
)
from undine.http.views import _handle_incremental, graphql_view_async, graphql_view_sync  # noqa: PLC2701
from undine.typing import GQLInfo, RequestMethod


def sync_resolver(obj: Any, info: GQLInfo) -> str:
    return "Hello, World!"


async def async_resolver(obj: Any, info: GQLInfo) -> str:  # noqa: RUF029
    return "Hello, World!"


example_schema = GraphQLSchema(
    query=GraphQLObjectType(
        "Query",
        fields={
            "hello": GraphQLField(
                GraphQLString,
                resolve=sync_resolver,
            ),
        },
    ),
)


example_async_schema = GraphQLSchema(
    query=GraphQLObjectType(
        "Query",
        fields={
            "hello": GraphQLField(
                GraphQLString,
                resolve=async_resolver,
            ),
        },
    ),
)


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "HEAD"])
def test_graphql_view__method_not_allowed(method: RequestMethod, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    request = MockRequest(
        method=method,
        accepted_types=[MediaType("*/*")],
        body=b'{"query": "query { hello }"}',
    )
    response = graphql_view_sync(request)  # type: ignore[arg-type]

    assert isinstance(response, HttpMethodNotAllowedResponse)

    assert response.status_code == 405
    assert response["Allow"] == "GET, POST"
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    assert response.content.decode() == "Method not allowed"


def test_graphql_view__content_negotiation__get_request(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    request = MockRequest(
        method="GET",
        accepted_types=[MediaType("*/*")],
    )
    request.GET.appendlist("query", "query { hello }")
    response = graphql_view_sync(request)  # type: ignore[arg-type]

    assert isinstance(response, HttpResponse)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/graphql-response+json"

    data = json.loads(response.content.decode())
    assert data == {"data": {"hello": "Hello, World!"}}


def test_graphql_view__content_negotiation__all_types(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("*/*")],
        body=b'{"query": "query { hello }"}',
    )
    response = graphql_view_sync(request)  # type: ignore[arg-type]

    assert isinstance(response, HttpResponse)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/graphql-response+json"

    data = json.loads(response.content.decode())
    assert data == {"data": {"hello": "Hello, World!"}}


def test_graphql_view__content_negotiation__graphql_json(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("application/graphql-response+json")],
        body=b'{"query": "query { hello }"}',
    )
    response = graphql_view_sync(request)  # type: ignore[arg-type]

    assert isinstance(response, HttpResponse)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/graphql-response+json"

    data = json.loads(response.content.decode())
    assert data == {"data": {"hello": "Hello, World!"}}


def test_graphql_view__content_negotiation__application_json(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("application/json")],
        body=b'{"query": "query { hello }"}',
    )
    response = graphql_view_sync(request)  # type: ignore[arg-type]

    assert isinstance(response, HttpResponse)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"

    data = json.loads(response.content.decode())
    assert data == {"data": {"hello": "Hello, World!"}}


def test_graphql_view__content_negotiation__application_xml(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("application/xml")],
        body=b'{"query": "query { hello }"}',
    )
    response = graphql_view_sync(request)  # type: ignore[arg-type]

    assert isinstance(response, HttpResponse)

    assert response.status_code == 406
    assert response["Accept"] == "application/graphql-response+json, application/json"
    assert response.content.decode() == "Server does not support any of the requested content types."


def test_graphql_view__content_negotiation__form_urlencoded(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    data = {"query": "query { hello }"}
    body = urllib.parse.urlencode(data, quote_via=urllib.parse.quote).encode("utf-8")

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("application/json")],
        content_type="application/x-www-form-urlencoded",
        body=body,
        POST=QueryDict(body, encoding="utf-8"),
    )

    response = graphql_view_sync(request)  # type: ignore[arg-type]

    assert isinstance(response, HttpResponse)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"

    data = json.loads(response.content.decode())
    assert data == {"data": {"hello": "Hello, World!"}}


def test_graphql_view__content_negotiation__multipart_form_data(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    data: dict[str, str | bytes] = {"query": "query { hello }"}
    request = create_multipart_form_data_request(data=data)

    response = graphql_view_sync(request)  # type: ignore[arg-type]

    assert isinstance(response, HttpResponse)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"

    data = json.loads(response.content.decode())
    assert data == {"data": {"hello": "Hello, World!"}}


def test_graphql_view__content_negotiation__test_html(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.GRAPHIQL_ENABLED = True

    request = MockRequest(
        method="GET",
        accepted_types=[MediaType("text/html")],
    )

    response = graphql_view_sync(request)

    assert isinstance(response, HttpResponse)

    assert response.status_code == 200
    assert response["Content-Type"] == "text/html; charset=utf-8"


def test_graphql_view__content_negotiation__unsupported_type(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("text/plain")],
        body=b'{"query": "query { hello }"}',
    )
    response = graphql_view_sync(request)  # type: ignore[arg-type]

    assert isinstance(response, HttpUnsupportedContentTypeResponse)

    assert response.status_code == 406
    assert response["Accept"] == "application/graphql-response+json, application/json"
    assert response.content.decode() == "Server does not support any of the requested content types."


def test_graphql_view__content_negotiation__multiple_types(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    request = MockRequest(
        method="POST",
        # First type is not supported, so the second type is used.
        accepted_types=[MediaType("text/plain"), MediaType("application/json")],
        body=b'{"query": "query { hello }"}',
    )
    response = graphql_view_sync(request)  # type: ignore[arg-type]

    assert isinstance(response, HttpResponse)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"

    data = json.loads(response.content.decode())
    assert data == {"data": {"hello": "Hello, World!"}}


def test_graphql_view__reverse(undine_settings) -> None:
    path = reverse(f"undine:{undine_settings.GRAPHQL_VIEW_NAME}")
    assert path == f"/{undine_settings.GRAPHQL_PATH}"


def test_graphql_view__async_resolver(undine_settings) -> None:
    undine_settings.SCHEMA = example_async_schema

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("*/*")],
        body=b'{"query": "query { hello }"}',
    )
    response = graphql_view_sync(request)  # type: ignore[arg-type]

    assert isinstance(response, HttpResponse)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/graphql-response+json"

    data = json.loads(response.content.decode())

    assert data == {
        "data": None,
        "errors": [
            {
                "message": "GraphQL execution failed to complete synchronously.",
                "extensions": {
                    "status_code": 500,
                    "error_code": "ASYNC_NOT_SUPPORTED",
                },
            }
        ],
    }


def test_graphql_view__async_resolver__async_endpoint(undine_settings) -> None:
    undine_settings.SCHEMA = example_async_schema
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("*/*")],
        body=b'{"query": "query { hello }"}',
    )
    coro = graphql_view_async(request)  # type: ignore[arg-type]

    assert iscoroutine(coro)

    response = asyncio.run(coro)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"

    data = json.loads(response.content.decode())

    assert data == {"data": {"hello": "Hello, World!"}}


def test_graphql_view__content_negotiation__event_stream(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.GRAPHIQL_ENABLED = True
    undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1 = True

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("text/event-stream")],
        body=b'{"query": "query { hello }"}',
    )

    coro = graphql_view_async(request)  # type: ignore[arg-type]

    assert iscoroutine(coro)

    response = asyncio.run(coro)

    assert isinstance(response, StreamingHttpResponse)

    assert response.status_code == 200
    assert response["Content-Type"] == "text/event-stream"
    assert response["Connection"] == "keep-alive"
    assert response["Cache-Control"] == "no-cache, no-store, must-revalidate"


def test_graphql_view__content_negotiation__multipart_mixed(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.GRAPHIQL_ENABLED = True

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("multipart/mixed; subscriptionSpec=1.0")],
        body=b'{"query": "query { hello }"}',
    )

    coro = graphql_view_async(request)  # type: ignore[arg-type]

    assert iscoroutine(coro)

    response = asyncio.run(coro)

    assert isinstance(response, StreamingHttpResponse)

    assert response.status_code == 200
    assert response["Content-Type"] == "multipart/mixed; boundary=graphql; subscriptionspec=1.0"


def test_graphql_view__async__parse_error(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("application/json")],
        body=b"not json",
    )

    with patch(
        "undine.http.views.GraphQLRequestParamsParser.run_async",
        new_callable=AsyncMock,
        side_effect=GraphQLError("parse error"),
    ):
        coro = graphql_view_async(request)  # type: ignore[arg-type]
        assert iscoroutine(coro)
        response = asyncio.run(coro)

    assert isinstance(response, HttpResponse)
    assert response.status_code == 200

    data = json.loads(response.content.decode())
    assert data == {
        "data": None,
        "errors": [
            {
                "message": "parse error",
                "extensions": {"status_code": 400},
            },
        ],
    }


def test_graphql_view__event_stream__http1_sse_not_allowed(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1 = False

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("text/event-stream")],
        body=b'{"query": "query { hello }"}',
        META={"SERVER_PROTOCOL": "HTTP/1.1"},
    )

    coro = graphql_view_async(request)  # type: ignore[arg-type]
    assert iscoroutine(coro)
    response = asyncio.run(coro)

    assert isinstance(response, HttpEventSourcingNotAllowedResponse)
    assert response.status_code == 426
    assert response["Upgrade"] == "HTTP/2.0"


def test_graphql_view__event_stream__parse_error(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1 = True

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("text/event-stream")],
        body=b"not json",
    )

    with patch(
        "undine.http.views.GraphQLRequestParamsParser.run_async",
        new_callable=AsyncMock,
        side_effect=GraphQLError("sse parse error"),
    ):
        coro = graphql_view_async(request)  # type: ignore[arg-type]
        assert iscoroutine(coro)
        response = asyncio.run(coro)

    assert isinstance(response, StreamingHttpResponse)
    assert response.status_code == 200
    assert response["Content-Type"] == "text/event-stream"


def test_graphql_view__multipart_mixed_subscription__parse_error(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("multipart/mixed; subscriptionSpec=1.0")],
        body=b"not json",
    )

    with patch(
        "undine.http.views.GraphQLRequestParamsParser.run_async",
        new_callable=AsyncMock,
        side_effect=GraphQLError("multipart parse error"),
    ):
        coro = graphql_view_async(request)  # type: ignore[arg-type]
        assert iscoroutine(coro)
        response = asyncio.run(coro)

    assert isinstance(response, StreamingHttpResponse)
    assert response.status_code == 200
    assert response["Content-Type"] == "multipart/mixed; boundary=graphql; subscriptionspec=1.0"


def _make_incremental_mocks():
    """Return a context manager that patches incremental module functions."""
    fake_module = types.ModuleType("undine.utils.graphql.incremental")

    async def fake_execute(params, request):  # noqa: RUF029
        yield object()  # type: ignore[misc]

    async def fake_result_to_response(result):  # noqa: RUF029
        yield object()  # type: ignore[misc]

    async def fake_heartbeat(stream):
        async for event in stream:
            yield event

    fake_module.execute_graphql_incremental = fake_execute
    fake_module.result_to_incremental_response = fake_result_to_response
    fake_module.with_incremental_stream_heartbeat = fake_heartbeat

    return patch.dict(sys.modules, {"undine.utils.graphql.incremental": fake_module})


def test_graphql_view__incremental__success(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    response_content_type = MediaType("multipart/mixed")
    add_media_type_param(response_content_type, name="boundary", value="graphql")

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("multipart/mixed")],
        body=b'{"query": "query { hello }"}',
        response_content_type=response_content_type,
    )

    with _make_incremental_mocks():
        coro = _handle_incremental(request)  # type: ignore[arg-type]
        assert iscoroutine(coro)
        response = asyncio.run(coro)

    assert isinstance(response, StreamingHttpResponse)
    assert response.status_code == 200
    assert response["Content-Type"] == "multipart/mixed; boundary=graphql"
    assert response["Connection"] == "keep-alive"
    assert response["Cache-Control"] == "no-cache, no-store, must-revalidate"


def test_graphql_view__incremental__parse_error(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    response_content_type = MediaType("multipart/mixed")
    add_media_type_param(response_content_type, name="boundary", value="graphql")

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("multipart/mixed")],
        body=b"not json",
        response_content_type=response_content_type,
    )

    with (
        _make_incremental_mocks(),
        patch(
            "undine.http.views.GraphQLRequestParamsParser.run_async",
            new_callable=AsyncMock,
            side_effect=GraphQLError("incremental parse error"),
        ),
    ):
        coro = _handle_incremental(request)  # type: ignore[arg-type]
        assert iscoroutine(coro)
        response = asyncio.run(coro)

    assert isinstance(response, StreamingHttpResponse)
    assert response.status_code == 200
    assert response["Content-Type"] == "multipart/mixed; boundary=graphql"


def test_graphql_view__async__routes_to_incremental(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    response_content_type = MediaType("multipart/mixed")
    add_media_type_param(response_content_type, name="boundary", value="graphql")

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("multipart/mixed")],
        body=b'{"query": "query { hello }"}',
        response_content_type=response_content_type,
    )

    with _make_incremental_mocks():
        # Bypass the decorator so the incremental branch is hit
        coro = graphql_view_async.__wrapped__(request)  # type: ignore[attr-defined]
        assert iscoroutine(coro)
        response = asyncio.run(coro)

    assert isinstance(response, StreamingHttpResponse)
    assert response.status_code == 200
    assert response["Content-Type"] == "multipart/mixed; boundary=graphql"
