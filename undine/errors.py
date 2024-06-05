from __future__ import annotations

from functools import wraps
from typing import Callable, ParamSpec

from graphql import ExecutionResult, GraphQLError

P = ParamSpec("P")

__all__ = [
    "GraphQLErrorGroup",
    "convert_errors_to_execution_result",
]


class GraphQLErrorGroup(Exception):  # noqa: N818
    def __init__(self, errors: list[GraphQLError]) -> None:
        self.errors = errors


def convert_errors_to_execution_result(func: Callable[P, ExecutionResult]) -> Callable[P, ExecutionResult]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> ExecutionResult:
        try:
            return func(*args, **kwargs)
        except GraphQLError as error:
            return ExecutionResult(errors=[error])
        except GraphQLErrorGroup as group:
            return ExecutionResult(errors=group.errors)
        except Exception as error:  # noqa: BLE001
            return ExecutionResult(errors=[GraphQLError(message=str(error))])

    return wrapper
