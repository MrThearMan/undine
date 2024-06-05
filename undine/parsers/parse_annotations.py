from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from django.db.models import QuerySet
from graphql import GraphQLResolveInfo, Undefined

from undine.dataclasses import Parameter
from undine.exceptions import MissingFunctionAnnotationsError, MissingFunctionReturnTypeError, NoFunctionParametersError
from undine.typing import GQLInfo
from undine.utils.reflection import get_signature, is_subclass

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FunctionType


__all__ = [
    "parse_first_param_type",
    "parse_parameters",
    "parse_return_annotation",
]


def parse_parameters(func: FunctionType | Callable[..., Any], *, depth: int = 0) -> list[Parameter]:
    """
    Parse function arguments, type hints, and default values into parameters.
    Only parses arguments that can be converted to GraphQL arguments.

    :param func: Function to parse.
    :param depth: How many function calls deep is the code calling this method compared to the parsed function?
                  This can be omitted if the function's signature has been parsed previously.
    """
    sig = get_signature(func, depth=depth + 1)

    missing: list[str] = []
    parameters: list[Parameter] = []

    for i, param in enumerate(sig.parameters.values()):
        # 'self' and 'cls' parameters are special and thus skipped.
        if param.name in {"self", "cls"} and i == 0:
            continue

        # Don't include '*args' and '**kwargs' parameters, as they are not supported by GraphQL.
        if param.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
            continue

        if param.annotation is inspect.Parameter.empty:
            missing.append(param.name)
            continue

        if param.annotation in {GraphQLResolveInfo, GQLInfo}:
            continue

        if is_subclass(param.annotation, QuerySet):
            continue

        parameters.append(
            Parameter(
                name=param.name,
                annotation=param.annotation,
                default_value=param.default if param.default is not inspect.Parameter.empty else Undefined,
            ),
        )

    if missing:
        raise MissingFunctionAnnotationsError(missing=missing, func=func) from None

    return parameters


def parse_first_param_type(func: FunctionType | Callable[..., Any], *, depth: int = 0) -> type:
    """
    Get the type of the first parameter of the given function.

    :param func: Function to parse.
    :param depth: How many function calls deep is the code calling this method compared to the parsed function?
                  This can be omitted if the function's signature has been parsed previously.
    """
    parameters = parse_parameters(func, depth=depth + 1)

    param_type = next((param.annotation for param in parameters), Undefined)
    if param_type is Undefined:
        raise NoFunctionParametersError(func=func)

    return param_type


def parse_return_annotation(func: FunctionType | Callable[..., Any], *, depth: int = 0) -> type:
    """
    Parse the return annotation of the given function.

    :param func: Function to parse.
    :param depth: How many function calls deep is the code calling this method compared to the parsed function?
                  This can be omitted if the function's signature has been parsed previously.
    """
    sig = get_signature(func, depth=depth + 1)

    if sig.return_annotation is inspect.Parameter.empty:
        raise MissingFunctionReturnTypeError(func=func) from None

    return sig.return_annotation
