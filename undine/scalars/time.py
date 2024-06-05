from __future__ import annotations

import datetime
from inspect import cleandoc

from django.utils import dateparse

from undine.exceptions import GraphQLScalarInvalidValueError

from ._definition import ScalarType

__all__ = [
    "GraphQLTime",
    "time_scalar",
]


time_scalar: ScalarType[datetime.time, str] = ScalarType(
    name="Time",
    description=cleandoc(
        """
        Represents a time value as specified by ISO 8601.
        Maps to the Python `datetime.time` type.
        """
    ),
    specified_by_url="https://datatracker.ietf.org/doc/html/rfc3339#section-5.6",
)

GraphQLTime = time_scalar.as_graphql_scalar()


@time_scalar.parse.register
def _(value: str) -> datetime.time:
    parsed_value = dateparse.parse_time(value)
    if parsed_value is None:
        raise GraphQLScalarInvalidValueError(typename="time")

    return parsed_value


@time_scalar.serialize.register
def _(value: str) -> str:
    parsed_value = dateparse.parse_time(value)
    if parsed_value is None:
        raise GraphQLScalarInvalidValueError(typename="time")

    return parsed_value.isoformat()


@time_scalar.serialize.register
def _(value: datetime.time) -> str:
    return value.replace(tzinfo=None).isoformat()


@time_scalar.serialize.register
def _(value: datetime.datetime) -> str:
    return value.time().isoformat()
