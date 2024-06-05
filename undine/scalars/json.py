from __future__ import annotations

import json
from inspect import cleandoc

from undine.exceptions import GraphQLScalarInvalidValueError

from ._definition import ScalarType

__all__ = [
    "GraphQLJSON",
    "json_scalar",
]


json_scalar: ScalarType[dict, dict] = ScalarType(
    name="JSON",
    description=cleandoc(
        """
        Represents a JSON serializable object.
        Maps to the Python `dict` type.
        """
    ),
    specified_by_url="https://datatracker.ietf.org/doc/html/rfc8259",
)

GraphQLJSON = json_scalar.as_graphql_scalar()


@json_scalar.serialize.register
@json_scalar.parse.register
def _(value: dict) -> dict:
    return value


@json_scalar.serialize.register
@json_scalar.parse.register
def _(value: str) -> dict:
    value = json.loads(value)
    if not isinstance(value, dict):
        raise GraphQLScalarInvalidValueError(typename="JSON")

    return value


@json_scalar.serialize.register
def _(value: bytes) -> dict:
    value = json.loads(value)
    if not isinstance(value, dict):
        raise GraphQLScalarInvalidValueError(typename="JSON")

    return value
