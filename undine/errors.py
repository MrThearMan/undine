from __future__ import annotations

from functools import wraps
from typing import Any, Callable, ParamSpec

from graphql import ExecutionResult, GraphQLError

P = ParamSpec("P")

__all__ = [
    "GraphQLStatusError",
    "convert_errors_to_execution_result",
]


class GraphQLStatusError(GraphQLError):
    def __init__(self, message: str, status_code: int = 400, **kwargs: Any) -> None:
        extensions = kwargs.setdefault("extensions", {})
        extensions["status_code"] = status_code
        super().__init__(message, **kwargs)


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
