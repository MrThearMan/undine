from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, ParamSpec, TypeVar

from graphql import ExecutionResult, GraphQLError, ValueNode, print_ast
from graphql.pyutils import inspect

from undine.utils import dotpath

if TYPE_CHECKING:
    from django.db import models

__all__ = [
    "GraphQLConversionError",
    "GraphQLStatusError",
    "convert_errors_to_execution_result",
    "handle_get_errors",
]

P = ParamSpec("P")
R = TypeVar("R")


class GraphQLStatusError(GraphQLError):
    def __init__(self, message: str, status_code: int = 400, **kwargs: Any) -> None:
        extensions = kwargs.setdefault("extensions", {})
        extensions["status_code"] = status_code
        super().__init__(message, **kwargs)


class GraphQLNotFoundError(GraphQLError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        extensions = kwargs.setdefault("extensions", {})
        extensions["error_code"] = "NOT_FOUND"
        extensions["status_code"] = 404
        super().__init__(message, **kwargs)


class GraphQLConversionError(GraphQLError):
    def __init__(self, name: str, value: Any, **kwargs: Any) -> None:
        if isinstance(value, ValueNode):
            kwargs["nodes"] = value
            kwargs["message"] = f"{name} cannot represent value: {print_ast(value)}"
        else:
            kwargs["message"] = f"{name} cannot represent value: {inspect(value)}"

        super().__init__(**kwargs)


def convert_errors_to_execution_result(func: Callable[P, ExecutionResult]) -> Callable[P, ExecutionResult]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> ExecutionResult:
        try:
            return func(*args, **kwargs)
        except GraphQLError as error:
            return ExecutionResult(errors=[error], extensions=error.extensions)
        except Exception as error:  # noqa: BLE001
            return ExecutionResult(errors=[GraphQLError(message=str(error))], extensions={"status_code": 500})

    return wrapper


def handle_conversion_errors(string: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return func(*args, **kwargs)
            except GraphQLConversionError:
                raise
            except Exception as error:
                raise GraphQLConversionError(string, args[0]) from error

        return wrapper

    return decorator


@contextmanager
def handle_get_errors(model: type[models.Model], **kwargs: Any) -> Any:
    """Handle `queryset.get` errors by raising an appropriate GraphQLError."""
    try:
        yield
    except model.DoesNotExist as error:
        msg = f"Cannot find any '{dotpath(model)}' object matching args: {kwargs}"
        raise GraphQLNotFoundError(message=msg) from error
    except model.MultipleObjectsReturned as error:
        msg = f"Found more than one '{dotpath(model)}' object matching args: {kwargs}"
        raise GraphQLNotFoundError(message=msg) from error
