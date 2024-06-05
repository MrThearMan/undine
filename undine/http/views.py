from __future__ import annotations

import json
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

from undine.execution import execute_graphql_from_request
from undine.settings import undine_settings

from .utils import HttpMethodNotAllowedResponse, HttpUnsupportedContentTypeResponse, get_preferred_response_content_type

if TYPE_CHECKING:
    from django.http import HttpRequest


__all__ = [
    "GraphQLView",
]


class GraphQLView(View):
    """A view for GraphQL requests."""

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if request.method not in {"GET", "POST"}:
            return HttpMethodNotAllowedResponse(allowed_methods=["GET", "POST"])

        supported_types = ["application/graphql-response+json", "application/json"]
        if undine_settings.GRAPHIQL_ENABLED:
            supported_types.append("text/html")

        media_type = get_preferred_response_content_type(accepted=request.accepted_types, supported=supported_types)
        if media_type is None:
            return HttpUnsupportedContentTypeResponse(supported_types=supported_types)

        if media_type == "text/html":
            return render(request, "undine/graphiql.html")

        result = execute_graphql_from_request(request)  # type: ignore[arg-type]

        content = json.dumps(result.formatted, separators=(",", ":"))
        return HttpResponse(content=content, status=HTTPStatus.OK, content_type=media_type)
