from __future__ import annotations

from types import FunctionType, NoneType, UnionType
from typing import Any, Union, get_args, get_origin

from graphql import GraphQLNonNull, GraphQLType

from undine.utils.reflection import is_not_required_type, is_required_type

from .parse_annotations import parse_first_param_type, parse_return_annotation

__all__ = [
    "parse_is_nullable",
]


def parse_is_nullable(ref: Any, *, is_input: bool = False) -> bool:
    # GraphQL doesn't differentiate between required and non-null...
    if is_required_type(ref):
        return False

    if is_not_required_type(ref):
        return True

    if isinstance(ref, GraphQLNonNull):
        return False

    if isinstance(ref, GraphQLType):
        return True

    if isinstance(ref, FunctionType):
        ref = parse_first_param_type(ref) if is_input else parse_return_annotation(ref)

    origin = get_origin(ref)
    if origin not in {UnionType, Union}:
        return False

    args = get_args(ref)
    return NoneType in args
