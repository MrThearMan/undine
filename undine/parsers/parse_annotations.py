from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

from graphql import GraphQLResolveInfo, Undefined

from undine.typing import Parameter
from undine.utils import dotpath, get_signature

if TYPE_CHECKING:
    from types import FunctionType


__all__ = [
    "parse_parameters",
    "parse_return_annotation",
]


def parse_parameters(func: FunctionType, *, depth: int = 0) -> list[Parameter]:
    """
    Parse function arguments, type hints, and default values into parameters.
    Only parses arguments that can be converted to GraphQL arguments.

    :param func: Function to parse.
    :param depth: How many function calls deep is the code calling this method compared to the parsed function?
    :raises RuntimeError: Function is missing a type hint for one of its arguments.
    """
    sig = get_signature(func, depth=depth + 1)

    missing: list[str] = []
    parameters: list[Parameter] = []

    for i, param in enumerate(sig.parameters.values()):
        # Method 'self' parameter is special and is skipped.
        if param.name == "self" and i == 0:
            continue

        # Don't include '*args' and '**kwargs' parameters, as they are not supported by GraphQL.
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue

        if param.annotation is inspect.Parameter.empty:
            missing.append(param.name)
            continue

        if isinstance(param.annotation, type) and issubclass(param.annotation, GraphQLResolveInfo):
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


def parse_return_annotation(func: FunctionType, *, depth: int = 0) -> type:
    """
    Parse the return annotation of the given function.

    :param func: Function to parse.
    :param depth: How many function calls deep is the code calling this method compared to the parsed function?
    :raises RuntimeError: Function is missing a type hint for its return value.
    """
    sig = get_signature(func, depth=depth + 1)  # type: ignore[arg-type]

    if sig.return_annotation is inspect.Parameter.empty:
        msg = f"Missing type hint for return value in function '{func.__name__}'."
        raise RuntimeError(msg) from None

    return sig.return_annotation
