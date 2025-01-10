from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

from django.core.exceptions import ValidationError
from graphql import ExecutionResult, GraphQLError
from graphql.pyutils import inspect

from undine.errors.exceptions import GraphQLConversionError
from undine.utils.logging import undine_logger

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "handle_conversion_errors",
    "handle_validation_errors",
    "raised_exceptions_as_execution_results",
]

P = ParamSpec("P")
T = TypeVar("T")


def handle_conversion_errors(typename: str):  # noqa: ANN201
    def decorator(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        @wraps(func)
        def wrapper(value: Any) -> Any:
            try:
                return func(value)
            except GraphQLConversionError:
                raise
            except Exception as error:
                raise GraphQLConversionError(typename=typename, value=inspect(value), error=str(error)) from error

        return wrapper

    return decorator


def handle_validation_errors(func: Callable[P, T]) -> Callable[P, T]:
    """Handle validation errors raised by Django's validators and reraise them as ValueErrors."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except ValidationError as error:
            if error.params is not None:
                error.message %= error.params
            raise ValueError(error.message) from error

    return wrapper


def raised_exceptions_as_execution_results(func: Callable[P, ExecutionResult]) -> Callable[P, ExecutionResult]:
    """Wraps raised exceptions as GraphQL ExecutionResults if they happen in `execute_graphql`."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> ExecutionResult:
        try:
            return func(*args, **kwargs)
        except Exception as error:  # noqa: BLE001
            undine_logger.error("Unexpected error in GraphQL execution", exc_info=error)
            return ExecutionResult(errors=[GraphQLError(message=str(error), extensions={"status_code": 500})])

    return wrapper
