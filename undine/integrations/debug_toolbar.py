from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from debug_toolbar.middleware import DebugToolbarMiddleware
from debug_toolbar.utils import is_processable_html_response
from django.core.serializers.json import DjangoJSONEncoder
from django.http.request import MediaType
from django.template.loader import render_to_string
from django.utils.encoding import force_str

from undine.settings import undine_settings

if TYPE_CHECKING:
    from debug_toolbar.toolbar import DebugToolbar
    from django.http import HttpRequest, HttpResponse

__all__ = [
    "monkeypatch_middleware",
]


def monkeypatch_middleware() -> None:
    """Insert additional GraphiQL handling to the debug toolbar middleware."""
    original_postprocess = DebugToolbarMiddleware._postprocess  # noqa: SLF001

    def patched_postprocess(
        self: DebugToolbarMiddleware,
        request: HttpRequest,
        response: HttpResponse,
        toolbar: DebugToolbar,
    ) -> HttpResponse:
        response = original_postprocess(self, request, response, toolbar)
        if _is_graphql_view(request):
            handle_graphiql(request, response, toolbar)
        return response

    DebugToolbarMiddleware._postprocess = patched_postprocess  # noqa: SLF001


def handle_graphiql(request: HttpRequest, response: HttpResponse, toolbar: DebugToolbar) -> None:
    """Add debug toolbar data to GraphiQL view responses."""
    if is_processable_html_response(response):
        add_toolbar_update_script(response)
        return

    if not _is_json_response(response):
        return

    if _is_introspection_query(request):
        return

    add_debug_toolbar_data(response, toolbar)
    return


def add_toolbar_update_script(response: HttpResponse) -> None:
    """Add the JS script to the GraphiQL template for updating the toolbar after a request."""
    template = render_to_string("undine/graphiql_debug_toolbar_patch.html")
    response.write(template)
    if "Content-Length" in response:
        response["Content-Length"] = len(response.content)


def add_debug_toolbar_data(response: HttpResponse, toolbar: DebugToolbar) -> None:
    """
    Add data for the debug toolbar to the response.
    Will be used by '/template/undine/patch_debug_toolbar.html'.
    """
    content = force_str(response.content, encoding=response.charset)
    payload = json.loads(content)

    payload["debugToolbar"] = {"storeId": toolbar.store_id, "panels": {}}

    for panel in reversed(toolbar.enabled_panels):
        payload["debugToolbar"]["panels"][panel.panel_id] = {
            "toolbarTitle": _call_if_callable(panel.nav_subtitle),
            "panelTitle": _call_if_callable(panel.title) if panel.has_content else None,
        }

    response.content = json.dumps(payload, cls=DjangoJSONEncoder)
    if "Content-Length" in response:
        response["Content-Length"] = len(response.content)


def _is_json_response(response: HttpResponse) -> bool:
    if getattr(response, "streaming", False):
        return False

    content_encoding = response.get("Content-Encoding", "")
    if content_encoding:
        return False

    content_type = response.get("Content-Type", "")
    if not content_type:
        return False

    media_type = MediaType(content_type)

    return media_type.match("application/json") or media_type.match("application/graphql-response+json")


def _is_introspection_query(request: HttpRequest) -> bool:
    try:
        body = json.loads(request.body)
    except Exception:  # noqa: BLE001
        return False

    return body.get("operationName") == "IntrospectionQuery"


def _is_graphql_view(request: HttpRequest) -> bool:
    if request.resolver_match is None:
        return False

    return request.resolver_match.view_name == f"undine:{undine_settings.GRAPHQL_VIEW_NAME}"


def _call_if_callable(obj: Any) -> Any:
    if callable(obj):
        return obj()
    return obj
