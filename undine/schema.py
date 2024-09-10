"""Functions for creating a GraphQL schema and executing queries against it."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Collection, Literal

from graphql import (
    ExecutionResult,
    GraphQLDirective,
    GraphQLError,
    GraphQLNamedType,
    GraphQLObjectType,
    GraphQLSchema,
    OperationType,
    execute,
    get_operation_ast,
    parse,
    specified_directives,
    specified_rules,
    validate,
    validate_schema,
)

from undine.errors.error_handlers import raised_exceptions_as_execution_results
from undine.fields import Entrypoint
from undine.settings import undine_settings
from undine.utils.reflection import get_members
from undine.utils.text import get_docstring, get_schema_name

if TYPE_CHECKING:
    from undine.typing import GraphQLParams


__all__ = [
    "create_schema",
    "execute_graphql",
]


def create_schema(  # noqa: PLR0913
    *,
    query_class: type | None = None,
    mutation_class: type | None = None,
    subscription_class: type | None = None,
    schema_description: str | None = None,
    additional_types: Collection[GraphQLNamedType] | None = None,
    additional_directives: Collection[GraphQLDirective] | None = None,
    query_extensions: dict[str, Any] | None = None,
    mutation_extensions: dict[str, Any] | None = None,
    subscription_extensions: dict[str, Any] | None = None,
    schema_extensions: dict[str, Any] | None = None,
) -> GraphQLSchema:
    """Creates the GraphQL schema."""
    query_object_type = _create_object_type(query_class, query_extensions)
    mutation_object_type = _create_object_type(mutation_class, mutation_extensions)
    subscription_object_type = _create_object_type(subscription_class, subscription_extensions)

    return GraphQLSchema(
        query=query_object_type,
        mutation=mutation_object_type,
        subscription=subscription_object_type,
        types=additional_types,
        directives=(*specified_directives, *additional_directives) if additional_directives else None,
        description=schema_description,
        extensions=schema_extensions,
    )


@raised_exceptions_as_execution_results
def execute_graphql(params: GraphQLParams, method: Literal["GET", "POST"], context_value: Any) -> ExecutionResult:
    """
    Executes a GraphQL query.

    :param params: GraphQL query parameters including the query, variables, and operation name.
    :param method: The HTTP method of the GraphQL request.
    :param context_value: The context value for the GraphQL execution.
    """
    schema_validation_errors = validate_schema(undine_settings.SCHEMA)
    if schema_validation_errors:
        return ExecutionResult(errors=schema_validation_errors, extensions={"status_code": 400})

    try:
        document = parse(
            source=params.query,
            no_location=not undine_settings.ADD_ERROR_LOCATION,
            max_tokens=undine_settings.MAX_TOKENS,
        )
    except GraphQLError as parse_error:
        return ExecutionResult(errors=[parse_error], extensions={"status_code": 400})

    if method == "GET":
        operation_node = get_operation_ast(document, params.operation_name)
        if getattr(operation_node, "operation", None) != OperationType.QUERY:
            msg = "Only query operations are allowed on GET requests."
            return ExecutionResult(errors=[GraphQLError(message=msg)], extensions={"status_code": 405})

    validation_errors = validate(
        schema=undine_settings.SCHEMA,
        document_ast=document,
        rules=(*specified_rules, *undine_settings.ADDITIONAL_VALIDATION_RULES),
        max_errors=undine_settings.MAX_ERRORS,
    )
    if validation_errors:
        return ExecutionResult(errors=validation_errors, extensions={"status_code": 400})

    return execute(
        schema=undine_settings.SCHEMA,
        document=document,
        root_value=undine_settings.ROOT_VALUE,
        context_value=context_value,
        variable_values=params.variables,
        operation_name=params.operation_name,
        middleware=undine_settings.MIDDLEWARE,
    )


def _create_object_type(cls: type | None, extensions: dict[str, Any] | None = None) -> GraphQLObjectType | None:
    if cls is None:
        return None

    return GraphQLObjectType(
        cls.__name__,
        fields={get_schema_name(name): entr.get_graphql_field() for name, entr in get_members(cls, Entrypoint)},
        extensions=extensions,
        description=get_docstring(cls),
    )
