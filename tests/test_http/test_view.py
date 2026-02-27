from __future__ import annotations

import asyncio
import json
import urllib.parse
from inspect import iscoroutine
from typing import Any

import pytest
from django.http import HttpResponse, StreamingHttpResponse
from django.http.request import MediaType, QueryDict
from django.urls import reverse
from graphql import GraphQLField, GraphQLObjectType, GraphQLSchema, GraphQLString

from tests.helpers import MockRequest, create_multipart_form_data_request
from undine.http.utils import HttpMethodNotAllowedResponse, HttpUnsupportedContentTypeResponse
from undine.http.views import graphql_view_async, graphql_view_sync
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
    assert response["Content-Type"] == "application/graphql-response+json"

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
    assert response["Content-Type"] == "text/event-stream; charset=utf-8"
    assert response["Connection"] == "keep-alive"
    assert response["Cache-Control"] == "no-cache"
    assert response["Content-Encoding"] == "none"


def test_graphql_view__content_negotiation__multipart_mixed(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.GRAPHIQL_ENABLED = True

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType('multipart/mixed;subscriptionSpec="1.0"'), MediaType("application/json")],
        body=b'{"query": "query { hello }"}',
    )

    coro = graphql_view_async(request)  # type: ignore[arg-type]

    assert iscoroutine(coro)

    response = asyncio.run(coro)

    assert isinstance(response, StreamingHttpResponse)

    assert response.status_code == 200
    assert response["Content-Type"] == 'multipart/mixed;boundary=graphql;subscriptionSpec="1.0", application/json'
