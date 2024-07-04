from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django.http import HttpResponse
from django.http.request import MediaType
from django.shortcuts import render
from django.views import View

from undine.execute import execute_graphql
from undine.parsers import GraphQLRequestParamsParser
from undine.settings import undine_settings
from undine.utils.query_logging import capture_database_queries

from .responses import HttpMethodNotAllowedResponse, HttpUnsupportedContentTypeResponse

if TYPE_CHECKING:
    from django.http import HttpRequest
    from graphql import ExecutionResult


__all__ = [
    "GraphQLView",
]


class GraphQLView(View):
    """A view for GraphQL requests."""

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if request.method not in ["GET", "POST"]:
            return HttpMethodNotAllowedResponse()

        media_type = self.get_first_supported_media_type(request)
        if media_type is None:
            return HttpUnsupportedContentTypeResponse()

        if media_type.main_type == "text" and media_type.sub_type == "html":
            return render(request, "undine/graphiql.html")

        params = GraphQLRequestParamsParser.run(request)
        with capture_database_queries():  # TODO: Debuging, remove later
            result = execute_graphql(params, request.method, request)
        return self.json_response(result, media_type)

    @staticmethod
    def get_first_supported_media_type(request: HttpRequest) -> MediaType | None:
        for accepted_type in request.accepted_types:
            if accepted_type.is_all_types:
                return MediaType("application/graphql-response+json; charset=utf-8")
            if (
                undine_settings.GRAPHIQL_ENABLED
                and accepted_type.main_type == "text"
                and accepted_type.sub_type == "html"
            ):
                return accepted_type
            if accepted_type.main_type == "application":
                if accepted_type.sub_type in "graphql-response+json":
                    return accepted_type
                if accepted_type.sub_type in "json":
                    return accepted_type
        return None

    @staticmethod
    def json_response(result: ExecutionResult, content_type: MediaType) -> HttpResponse:
        data = json.dumps(result.formatted, separators=(",", ":"))
        status_code = (result.extensions or {}).get("status_code", 200)
        return HttpResponse(content=data, status=status_code, content_type=str(content_type))
