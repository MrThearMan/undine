from __future__ import annotations

import datetime as dt
from inspect import cleandoc

from django.utils import dateparse

from undine.exceptions import GraphQLScalarInvalidValueError

from ._definition import ScalarType

__all__ = [
    "GraphQLDate",
    "date_scalar",
]


date_scalar: ScalarType[dt.date, str] = ScalarType(
    name="Date",
    description=cleandoc(
        """
        Represents a date value as specified by ISO 8601.
        Maps to the Python `datetime.date` type.
        """
    ),
    specified_by_url="https://datatracker.ietf.org/doc/html/rfc3339#section-5.6",
)

GraphQLDate = date_scalar.as_graphql_scalar()


@date_scalar.parse.register
def _(value: str) -> dt.date:
    parsed_value: dt.date | None = dateparse.parse_date(value)
    if parsed_value is None:
        raise GraphQLScalarInvalidValueError(typename="date")

    return parsed_value


@date_scalar.serialize.register
def _(value: str) -> str:
    parsed_value: dt.date | None = dateparse.parse_date(value)
    if parsed_value is None:
        raise GraphQLScalarInvalidValueError(typename="date")

    return parsed_value.isoformat()


@date_scalar.serialize.register
def _(value: dt.date) -> str:
    return value.isoformat()


@date_scalar.serialize.register
def _(value: dt.datetime) -> str:
    return value.date().isoformat()
