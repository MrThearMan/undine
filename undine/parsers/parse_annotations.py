from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Callable

from graphql import Undefined

from undine.parsers.parse_signature import parse_signature
from undine.typing import Parameter
from undine.utils import dotpath

if TYPE_CHECKING:
    from types import FunctionType


__all__ = [
    "parse_parameters",
    "parse_return_annotation",
]


def parse_parameters(func: FunctionType, *, level: int = 0) -> list[Parameter]:
    sig = parse_signature(func, level=level + 1)

    missing: list[str] = []
    parameters: list[Parameter] = []

    for i, param in enumerate(sig.parameters.values()):
        # Method 'self' parameter is special and is skipped.
        if param.name == "self" and i == 0:
            continue

        # Dont include '*args' and '**kwargs' parameters, as they are not supported by GraphQL.
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue

        if param.annotation is inspect.Parameter.empty:
            missing.append(param.name)
            continue

        parameters.append(
            Parameter(
                name=param.name,
                annotation=param.annotation,
                default_value=param.default if param.default is not inspect.Parameter.empty else Undefined,
            ),
        )

    if missing:
        msg = f"Missing type hints for parameters {missing} in function '{dotpath(func)}'."
        raise RuntimeError(msg) from None

    return parameters


def parse_return_annotation(func: FunctionType | Callable, *, level: int = 0) -> type:
    sig = parse_signature(func, level=level + 1)  # type: ignore[arg-type]

    if sig.return_annotation is inspect.Parameter.empty:
        msg = f"Missing type hint for return value in function '{func.__name__}'."
        raise RuntimeError(msg) from None

    return sig.return_annotation
