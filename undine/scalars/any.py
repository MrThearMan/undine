from __future__ import annotations

import datetime
import math
import uuid
from typing import Any

from graphql.type.scalars import GRAPHQL_MAX_INT, GRAPHQL_MIN_INT

from ._definition import ScalarType

__all__ = [
    "GraphQLAny",
    "any_scalar",
]


any_scalar: ScalarType[Any, Any] = ScalarType(
    name="Any",
    description="Represent any value accepted by GraphQL.",
)

GraphQLAny = any_scalar.as_graphql_scalar()


@any_scalar.serialize.register
@any_scalar.parse.register
def _(value: str | bool | None) -> Any:  # noqa: FBT001
    return value


@any_scalar.serialize.register
@any_scalar.parse.register
def _(value: bytes) -> Any:
    return value.decode(encoding="utf-8")


@any_scalar.serialize.register
@any_scalar.parse.register
def _(value: int) -> Any:
    if not (GRAPHQL_MIN_INT <= value <= GRAPHQL_MAX_INT):
        msg = "GraphQL integers cannot represent non 32-bit signed integer value."
        raise ValueError(msg)
    return value


@any_scalar.serialize.register
@any_scalar.parse.register
def _(value: float) -> Any:
    if not math.isfinite(value):
        msg = "GraphQL floats cannot represent 'inf' or 'NaN' values."
        raise ValueError(msg)
    return value


@any_scalar.serialize.register
@any_scalar.parse.register
def _(value: datetime.datetime | datetime.date | datetime.time) -> Any:
    return value.isoformat()


@any_scalar.serialize.register
@any_scalar.parse.register
def _(value: uuid.UUID) -> Any:
    return str(value)


@any_scalar.serialize.register
@any_scalar.parse.register
def _(value: list) -> Any:
    return [any_scalar.parse(value) for value in value]


@any_scalar.serialize.register
@any_scalar.parse.register
def _(value: dict) -> Any:
    return {key: any_scalar.parse(value) for key, value in value.items()}
