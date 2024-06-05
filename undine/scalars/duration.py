from __future__ import annotations

import datetime
from inspect import cleandoc

from undine.exceptions import GraphQLScalarInvalidValueError

from ._definition import ScalarType

__all__ = [
    "GraphQLDuration",
    "duration_scalar",
]

duration_scalar: ScalarType[datetime.timedelta, int] = ScalarType(
    name="Duration",
    description=cleandoc(
        """
        Represents a duration of time in seconds.
        Maps to the Python `datetime.timedelta` type.
        """
    ),
)

GraphQLDuration = duration_scalar.as_graphql_scalar()


@duration_scalar.parse.register
def _(value: int) -> datetime.timedelta:
    return datetime.timedelta(seconds=value)


@duration_scalar.parse.register
def _(value: str) -> datetime.timedelta:
    try:
        parsed_value = int(value)
    except ValueError as error:
        raise GraphQLScalarInvalidValueError(typename="integer") from error

    return datetime.timedelta(seconds=parsed_value)


@duration_scalar.serialize.register
def _(value: str) -> int:
    try:
        parsed_value = int(value)
    except ValueError as error:
        raise GraphQLScalarInvalidValueError(typename="integer") from error

    return int(datetime.timedelta(seconds=parsed_value).total_seconds())


@duration_scalar.serialize.register
def _(value: int) -> int:
    return int(datetime.timedelta(seconds=value).total_seconds())


@duration_scalar.serialize.register
def _(value: datetime.timedelta) -> int:
    return int(value.total_seconds())
