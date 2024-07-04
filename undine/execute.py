from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Literal, ParamSpec, TypeVar

from graphql import (
    ExecutionResult,
    GraphQLError,
    OperationType,
    execute,
    get_operation_ast,
    parse,
    specified_rules,
    validate,
    validate_schema,
)

from undine.settings import undine_settings

if TYPE_CHECKING:
    from undine.typing import GraphQLParams


__all__ = [
    "execute_graphql",
]


P = ParamSpec("P")
R = TypeVar("R")


def _convert_errors_to_execution_result(func: Callable[P, ExecutionResult]) -> Callable[P, ExecutionResult]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> ExecutionResult:
        try:
            return func(*args, **kwargs)
        except GraphQLError as error:
            return ExecutionResult(errors=[error], extensions=error.extensions)
        except Exception as error:  # noqa: BLE001
            return ExecutionResult(errors=[GraphQLError(message=str(error))], extensions={"status_code": 500})

    return wrapper


@_convert_errors_to_execution_result
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
