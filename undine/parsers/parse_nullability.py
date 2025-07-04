from __future__ import annotations

from types import FunctionType, NoneType, UnionType
from typing import Any, Union, get_origin

from graphql import GraphQLNonNull, GraphQLType

from undine.typing import ParametrizedType
from undine.utils.reflection import get_flattened_generic_params, is_not_required_type, is_required_type

from .parse_annotations import parse_first_param_type, parse_return_annotation

__all__ = [
    "parse_is_nullable",
]


def parse_is_nullable(ref: Any, *, is_input: bool = False, total: bool = True) -> bool:
    """
    Determine whether the given reference indicates a nullable GraphQL type or not.

    :param ref: The reference to check.
    :param is_input: Whether the reference is for an input or output type.
    :param total: If the reference is in a TypedDict, whether the TypedDict has totality of not.
    """
    # GraphQL doesn't differentiate between required and non-null...
    if not total:
        if not is_required_type(ref):
            return True

        args = get_flattened_generic_params(ref)
        return NoneType in args

    if is_not_required_type(ref):
        return True

    if isinstance(ref, GraphQLNonNull):
        return False

    if isinstance(ref, GraphQLType):
        return True

    if isinstance(ref, FunctionType):
        ref = parse_first_param_type(ref) if is_input else parse_return_annotation(ref)

    origin = get_origin(ref)
    if origin not in {UnionType, Union, ParametrizedType}:
        return False

    args = get_flattened_generic_params(ref)
    return NoneType in args
