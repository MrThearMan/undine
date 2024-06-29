from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django.http import HttpResponse
from django.http.request import MediaType
from django.shortcuts import render
from django.views import View
from graphql import (
    DocumentNode,
    ExecutionResult,
    GraphQLError,
    OperationType,
    execute,
    get_operation_ast,
    parse,
    validate,
    validate_schema,
)

from undine.errors import GraphQLStatusError, convert_errors_to_execution_result
from undine.http.request_parser import GraphQLRequestParamsParser
from undine.http.responses import HttpMethodNotAllowedResponse, HttpUnsupportedContentTypeResponse
from undine.settings import undine_settings
from undine.utils.query_logging import capture_database_queries

if TYPE_CHECKING:
    from django.http import HttpRequest


__all__ = [
    "GraphQLView",
]


class GraphQLView(View):
    """A view for GraphQL requests."""

    def __init__(self) -> None:
        self.schema = undine_settings.SCHEMA
        # TODO:
        self.middleware = None
        self.root_value = None
        self.field_resolver = None
        self.type_resolver = None
        self.subscribe_field_resolver = None
        self.no_location = False
        self.max_tokens = None
        self.max_errors = None
        self.validation_rules = None
        super().__init__()

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if request.method not in ["GET", "POST"]:
            return HttpMethodNotAllowedResponse()

        media_type = self.get_first_supported_media_type(request)
        if media_type is None:
            return HttpUnsupportedContentTypeResponse()

        if media_type.main_type == "text" and media_type.sub_type == "html":
            return render(request, "undine/graphiql.html")

        with capture_database_queries():
            result = self.execute_graphql(request)
        return self.json_response(result, media_type)

    @convert_errors_to_execution_result
    def execute_graphql(self, request: HttpRequest) -> ExecutionResult:
        params = GraphQLRequestParamsParser.run(request)

        schema_validation_errors = validate_schema(self.schema)
        if schema_validation_errors:
            return ExecutionResult(errors=schema_validation_errors, extensions={"status_code": 400})

        try:
            document = parse(
                source=params.query,
                no_location=self.no_location,
                max_tokens=self.max_tokens,
            )
        except GraphQLError as parse_error:
            return ExecutionResult(errors=[parse_error], extensions={"status_code": 400})

        if request.method == "GET":
            self.raise_if_not_query(document, params.operation_name)

        validation_errors = validate(
            schema=self.schema,
            document_ast=document,
            rules=self.validation_rules,
            max_errors=self.max_errors,
        )
        if validation_errors:
            return ExecutionResult(errors=validation_errors, extensions={"status_code": 400})

        return execute(
            schema=self.schema,
            document=document,
            root_value=self.root_value,
            context_value=request,
            variable_values=params.variables,
            operation_name=params.operation_name,
            field_resolver=self.field_resolver,
            type_resolver=self.type_resolver,
            subscribe_field_resolver=self.subscribe_field_resolver,
            middleware=self.middleware,
        )

    def get_first_supported_media_type(self, request: HttpRequest) -> MediaType | None:
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

    def raise_if_not_query(self, document: DocumentNode, operation_name: str) -> None:
        operation_node = get_operation_ast(document, operation_name)
        if getattr(operation_node, "operation", None) != OperationType.QUERY:
            msg = "Only query operations are allowed on GET requests."
            raise GraphQLStatusError(message=msg, status_code=405)

    def json_response(self, result: ExecutionResult, content_type: MediaType) -> HttpResponse:
        data = json.dumps(result.formatted, separators=(",", ":"))
        status_code = (result.extensions or {}).get("status_code", 200)
        return HttpResponse(content=data, status=status_code, content_type=str(content_type))
