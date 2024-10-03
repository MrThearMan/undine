from __future__ import annotations

from inspect import cleandoc
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
from django.http import HttpResponse
from django.http.request import MediaType
from django.middleware.csrf import get_token

from tests.helpers import MockRequest, override_undine_settings
from undine import GraphQLView
from undine.http.responses import HttpMethodNotAllowedResponse, HttpUnsupportedContentTypeResponse

if TYPE_CHECKING:
    from undine.typing import HttpMethod


@override_undine_settings(SCHEMA="undine.settings.example_schema")
@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "HEAD"])
def test_graphql_view__method_not_allowed(method: HttpMethod):
    view = GraphQLView.as_view()

    request = MockRequest(method=method)
    response = view(request=request)

    assert isinstance(response, HttpMethodNotAllowedResponse)

    assert response.content.decode() == "Method not allowed"
    assert response.status_code == 405
    assert response["Allow"] == "GET, POST"
    assert response["Content-Type"] == "text/plain; charset=utf-8"


@override_undine_settings(SCHEMA="undine.settings.example_schema")
def test_graphql_view__content_type__all_types():
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
    assert response["Content-Type"] == "application/graphql-response+json; charset=utf-8"


@override_undine_settings(SCHEMA="undine.settings.example_schema")
def test_graphql_view__content_type__graphql_json():
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


@override_undine_settings(SCHEMA="undine.settings.example_schema")
def test_graphql_view__content_type__application_json():
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


@override_undine_settings(SCHEMA="undine.settings.example_schema", GRAPHIQL_ENABLED=True)
def test_graphql_view__content_type__test_html():
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
        """
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "text/html; charset=utf-8"


@override_undine_settings(SCHEMA="undine.settings.example_schema")
def test_graphql_view__content_type__unsupported_type():
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
