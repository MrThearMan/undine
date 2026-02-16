from __future__ import annotations

import pytest
from django.template.loader import render_to_string

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
