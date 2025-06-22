from __future__ import annotations

import urllib.parse
from inspect import cleandoc
from typing import Any
from unittest.mock import patch

import pytest
from django.http import HttpResponse
from django.http.request import MediaType, QueryDict
from django.middleware.csrf import get_token
from graphql import GraphQLField, GraphQLObjectType, GraphQLSchema, GraphQLString

from tests.helpers import MockRequest, create_multipart_form_data_request
from undine import GraphQLView
from undine.http.utils import HttpMethodNotAllowedResponse, HttpUnsupportedContentTypeResponse
from undine.typing import HttpMethod

example_schema = GraphQLSchema(
    query=GraphQLObjectType(
        "Query",
        fields={
            "hello": GraphQLField(
                GraphQLString,
                resolve=lambda obj, info: "Hello, World!",  # noqa: ARG005
            ),
        },
    ),
)


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "HEAD"])
def test_graphql_view__method_not_allowed(method: HttpMethod, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    view = GraphQLView.as_view()

    request = MockRequest(
        method=method,
        accepted_types=[MediaType("*/*")],
        body=b'{"query": "query { hello }"}',
    )
    response = view(request=request)

    assert isinstance(response, HttpMethodNotAllowedResponse)

    assert response.content.decode() == "Method not allowed"
    assert response.status_code == 405
    assert response["Allow"] == "GET, POST"
    assert response["Content-Type"] == "text/plain; charset=utf-8"


def test_graphql_view__content_negotiation__get_request(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    view = GraphQLView.as_view()

    request = MockRequest(
        method="GET",
        accepted_types=[MediaType("*/*")],
    )
    request.GET.appendlist("query", "query { hello }")
    response = view(request=request)

    assert isinstance(response, HttpResponse)

    assert response.content.decode() == '{"data":{"hello":"Hello, World!"}}'
    assert response.status_code == 200
    assert response["Content-Type"] == "application/graphql-response+json"


def test_graphql_view__content_negotiation__all_types(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    view = GraphQLView.as_view()

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("*/*")],
        body=b'{"query": "query { hello }"}',
    )
    response = view(request=request)

    assert isinstance(response, HttpResponse)

    assert response.content.decode() == '{"data":{"hello":"Hello, World!"}}'
    assert response.status_code == 200
    assert response["Content-Type"] == "application/graphql-response+json"


def test_graphql_view__content_negotiation__graphql_json(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    view = GraphQLView.as_view()

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("application/graphql-response+json")],
        body=b'{"query": "query { hello }"}',
    )
    response = view(request=request)

    assert isinstance(response, HttpResponse)

    assert response.content.decode() == '{"data":{"hello":"Hello, World!"}}'
    assert response.status_code == 200
    assert response["Content-Type"] == "application/graphql-response+json"


def test_graphql_view__content_negotiation__application_json(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    view = GraphQLView.as_view()

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("application/json")],
        body=b'{"query": "query { hello }"}',
    )
    response = view(request=request)

    assert isinstance(response, HttpResponse)

    assert response.content.decode() == '{"data":{"hello":"Hello, World!"}}'
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"


def test_graphql_view__content_negotiation__application_xml(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    view = GraphQLView.as_view()

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("application/xml")],
        body=b'{"query": "query { hello }"}',
    )
    response = view(request=request)

    assert isinstance(response, HttpResponse)

    assert response.content.decode() == "Server does not support any of the requested content types."
    assert response.status_code == 406
    assert response["Accept"] == "application/graphql-response+json, application/json, text/html"


def test_graphql_view__content_negotiation__form_urlencoded(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    view = GraphQLView.as_view()

    data = {"query": "query { hello }"}
    body = urllib.parse.urlencode(data, quote_via=urllib.parse.quote).encode("utf-8")

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("application/json")],
        content_type="application/x-www-form-urlencoded",
        body=body,
        POST=QueryDict(body, encoding="utf-8"),
    )

    response = view(request=request)

    assert isinstance(response, HttpResponse)

    assert response.content.decode() == '{"data":{"hello":"Hello, World!"}}'
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"


def test_graphql_view__content_negotiation__multipart_form_data(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    view = GraphQLView.as_view()

    data: dict[str, str | bytes] = {"query": "query { hello }"}
    request = create_multipart_form_data_request(data=data)

    response = view(request=request)

    assert isinstance(response, HttpResponse)

    assert response.content.decode() == '{"data":{"hello":"Hello, World!"}}'
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"


def test_graphql_view__content_negotiation__test_html(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.GRAPHIQL_ENABLED = True

    view = GraphQLView.as_view()

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("text/html")],
        body=b'{"query": "query { hello }"}',
    )

    csrf: str = ""

    def hook(*args: Any, **kwargs: Any) -> Any:
        nonlocal csrf
        csrf = get_token(*args, **kwargs)
        return csrf

    with patch("django.template.context_processors.get_token", side_effect=hook):
        response = view(request=request)

    assert isinstance(response, HttpResponse)

    assert response.content.decode().strip() == cleandoc(
        f"""
        <!DOCTYPE html>
        <html lang="en-us">
        <head>
          <title>GraphiQL</title>
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <meta name="robots" content="noindex">
          <link rel="shortcut icon" type="image/png" href="data:image/png;base64,iVBORw0KGgo="/>

          <link rel="stylesheet" href="/static/undine/css/main.css">
          <link rel="stylesheet" href="/static/undine/vendor/graphiql.min.css">
          <link rel="stylesheet" href="/static/undine/vendor/plugin-explorer.css">

          <script src="/static/undine/vendor/react.development.js"></script>
          <script src="/static/undine/vendor/react-dom.development.js"></script>
          <script src="/static/undine/vendor/graphiql.min.js"></script>
          <script src="/static/undine/vendor/plugin-explorer.umd.js"></script>
        </head>
        <body style="background-color: hsl(var(--color-base))">
          <div id="graphiql"></div>
          <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
          <script src="/static/undine/js/main.js" defer></script>
        </body>
        </html>
        """,
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "text/html; charset=utf-8"


def test_graphql_view__content_negotiation__unsupported_type(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    view = GraphQLView.as_view()

    request = MockRequest(
        method="POST",
        accepted_types=[MediaType("text/plain")],
        body=b'{"query": "query { hello }"}',
    )
    response = view(request=request)

    assert isinstance(response, HttpUnsupportedContentTypeResponse)

    assert response.content.decode() == "Server does not support any of the requested content types."
    assert response.status_code == 406
    assert response["Accept"] == "application/graphql-response+json, application/json, text/html"


def test_graphql_view__content_negotiation__multiple_types(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    view = GraphQLView.as_view()

    request = MockRequest(
        method="POST",
        # First type is not supported, so the second type is used.
        accepted_types=[MediaType("text/plain"), MediaType("application/json")],
        body=b'{"query": "query { hello }"}',
    )
    response = view(request=request)

    assert isinstance(response, HttpResponse)

    assert response.content.decode() == '{"data":{"hello":"Hello, World!"}}'
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
