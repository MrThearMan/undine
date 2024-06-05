from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django.http import HttpResponse
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

from undine.errors import convert_errors_to_execution_result
from undine.parsers import GraphQLParamsParser
from undine.settings import undine_settings

if TYPE_CHECKING:
    from django.http import HttpRequest


__all__ = [
    "GraphQLView",
]


class GraphQLView(View):
    # TODO: status codes

    def __init__(self) -> None:
        self.schema = undine_settings.SCHEMA
        self.graphiql_enabled = undine_settings.GRAPHIQL_ENABLED
        self.middleware = None
        self.root_value = None
        self.field_resolver = None
        self.type_resolver = None
        self.subscribe_field_resolver = None
        self.execution_context_class = None
        self.no_location = False
        self.max_tokens = None
        self.allow_legacy_fragment_variables = False
        self.max_errors = None
        self.validation_rules = None
        self.response_content_type = undine_settings.RESPONSE_CONTENT_TYPE
        super().__init__()

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if request.method not in ["GET", "POST"]:
            msg = "Only GET and POST methods are allowed"
            result = ExecutionResult(errors=[GraphQLError(message=msg)])

        elif self.graphiql_enabled and self.prefers_html(request):
            return render(request, "undine/graphiql.html")

        else:
            result = self.execute_graphql(request)

        data = json.dumps(result.formatted, separators=(",", ":"))
        return HttpResponse(content=data, content_type=self.response_content_type)

    def prefers_html(self, request: HttpRequest) -> bool:
        for accepted_type in request.accepted_types:
            if accepted_type.main_type == "text" and accepted_type.sub_type == "html":
                return True
            if accepted_type.main_type == "application" and accepted_type.sub_type in ["json", "graphql-response+json"]:
                return False
        return False

    @convert_errors_to_execution_result
    def execute_graphql(self, request: HttpRequest) -> ExecutionResult:
        params = GraphQLParamsParser.run(request)

        schema_validation_errors = validate_schema(self.schema)
        if schema_validation_errors:
            return ExecutionResult(errors=schema_validation_errors)

        document = parse(
            source=params.query,
            no_location=self.no_location,
            max_tokens=self.max_tokens,
            allow_legacy_fragment_variables=self.allow_legacy_fragment_variables,
        )

        if request.method == "GET":
            self.check_operation(document, params.operation_name)

        validation_errors = validate(
            schema=self.schema,
            document_ast=document,
            rules=self.validation_rules,
            max_errors=self.max_errors,
        )
        if validation_errors:
            return ExecutionResult(errros=validation_errors)

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
            execution_context_class=self.execution_context_class,
        )

    def check_operation(self, document: DocumentNode, operation_name: str) -> None:
        operation_node = get_operation_ast(document, operation_name)
        if operation_node is not None and operation_node.operation != OperationType.QUERY:
            msg = f"{operation_node.operation.value.capitalize()} operations are not supported on GET requests."
            raise GraphQLError(message=msg)
