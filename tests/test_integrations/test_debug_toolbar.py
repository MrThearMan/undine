from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from debug_toolbar.middleware import DebugToolbarMiddleware
from django.http import HttpResponse, StreamingHttpResponse
from django.template.loader import render_to_string

from undine.integrations.debug_toolbar import (
    _is_graphql_view,  # noqa: PLC2701
    _is_introspection_query,  # noqa: PLC2701
    _is_json_response,  # noqa: PLC2701
    add_debug_toolbar_data,
    add_toolbar_update_script,
    handle_graphiql,
    monkeypatch_middleware,
)
from undine.settings import example_schema


@pytest.fixture(autouse=True)
def enable_debug_toolbar(settings):
    debug = settings.DEBUG
    middleware = "debug_toolbar.middleware.DebugToolbarMiddleware"

    if middleware in settings.MIDDLEWARE:
        settings.MIDDLEWARE.remove(middleware)

    try:
        settings.DEBUG = True
        settings.MIDDLEWARE.append(middleware)
        yield

    finally:
        settings.DEBUG = debug
        settings.MIDDLEWARE.remove(middleware)


def test_debug_toolbar(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema

    query = "query { testing }"

    response = graphql(query)

    assert response.has_errors is False, response.errors

    assert "debugToolbar" in response

    debug_toolbar = response["debugToolbar"]

    assert "requestId" in debug_toolbar
    assert "panels" in debug_toolbar

    panels = debug_toolbar["panels"]

    assert "AlertsPanel" in panels
    assert "CachePanel" in panels
    assert "HeadersPanel" in panels
    assert "RequestPanel" in panels
    assert "SQLPanel" in panels
    assert "SettingsPanel" in panels
    assert "SignalsPanel" in panels
    assert "StaticFilesPanel" in panels
    assert "TemplatesPanel" in panels
    assert "TimerPanel" in panels
    assert "VersionsPanel" in panels


def test_debug_toolbar__introspection_query(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema

    query = """
        query IntrospectionQuery {
          __schema {
            queryType { name }
          }
        }
    """

    response = graphql(query, operation_name="IntrospectionQuery")

    assert response.status_code == 200

    assert response.has_errors is False, response.errors

    assert "debugToolbar" not in response


def test_debug_toolbar__html(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema

    html_response = graphql.get(
        path=f"/{undine_settings.GRAPHQL_PATH}",
        content_type="application/json",
        headers={"Accept": "text/html"},
    )

    assert html_response.status_code == 200
    assert html_response.headers["Content-Type"] == "text/html; charset=utf-8"

    # Check that the GraphiQL patch is included in the HTML response.
    content = html_response.content.decode()
    graphiql_patch = render_to_string("undine/graphiql_debug_toolbar_patch.html")
    assert graphiql_patch in content


def test_is_json_response__streaming() -> None:
    response = StreamingHttpResponse(iter([b"chunk"]))
    assert _is_json_response(response) is False


def test_is_json_response__content_encoding() -> None:
    response = HttpResponse(content_type="application/json")
    response["Content-Encoding"] = "gzip"
    assert _is_json_response(response) is False


def test_is_json_response__no_content_type() -> None:
    response = HttpResponse()
    del response["Content-Type"]
    assert _is_json_response(response) is False


def test_is_introspection_query__invalid_json() -> None:
    request = MagicMock()
    request.body = b"not json"
    assert _is_introspection_query(request) is False


def test_is_graphql_view__no_resolver_match() -> None:
    request = MagicMock()
    request.resolver_match = None
    assert _is_graphql_view(request) is False


def test_handle_graphiql__non_json_non_html(undine_settings) -> None:
    response = HttpResponse(b"some data", content_type="text/plain")
    request = MagicMock()
    toolbar = MagicMock()
    handle_graphiql(request, response, toolbar)
    # Should return early without modifying response
    toolbar.assert_not_called()


def test_add_toolbar_update_script__with_content_length() -> None:
    response = HttpResponse(content_type="text/html")
    response["Content-Length"] = str(len(response.content))
    add_toolbar_update_script(response)
    # Content-Length should be updated after writing the template
    assert int(response["Content-Length"]) == len(response.content)


def test_patched_postprocess__non_graphql_view(undine_settings) -> None:
    monkeypatch_middleware()

    middleware_instance = DebugToolbarMiddleware(lambda _: None)
    request = MagicMock()
    request.resolver_match = None  # not a graphql view
    response = HttpResponse("OK")
    toolbar = MagicMock()

    with patch.object(DebugToolbarMiddleware, "_postprocess", side_effect=lambda _req, resp, _tb: resp):
        result = middleware_instance._postprocess(request, response, toolbar)

    assert result is response


def test_add_debug_toolbar_data__store_id_fallback() -> None:
    response = HttpResponse(json.dumps({"data": {}}), content_type="application/json")
    toolbar = MagicMock(spec=[])  # no request_id → AttributeError
    toolbar.store_id = "abc123"
    toolbar.enabled_panels = []

    add_debug_toolbar_data(response, toolbar)

    payload = json.loads(response.content)
    assert payload["debugToolbar"]["requestId"] == "abc123"


def test_add_debug_toolbar_data__updates_content_length() -> None:
    body = json.dumps({"data": {}})
    response = HttpResponse(body, content_type="application/json")
    response["Content-Length"] = str(len(response.content))

    toolbar = MagicMock()
    toolbar.request_id = "xyz"
    toolbar.enabled_panels = []

    add_debug_toolbar_data(response, toolbar)

    assert int(response["Content-Length"]) == len(response.content)
