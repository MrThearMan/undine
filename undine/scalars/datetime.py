from __future__ import annotations

import datetime
import zoneinfo
from inspect import cleandoc

from django.conf import settings
from django.utils import dateparse
from django.utils.timezone import get_default_timezone, is_naive

from undine.exceptions import GraphQLScalarInvalidValueError

from ._definition import ScalarType

__all__ = [
    "GraphQLDateTime",
    "datetime_scalar",
]


datetime_scalar: ScalarType[datetime.datetime, str] = ScalarType(
    name="DateTime",
    description=cleandoc(
        """
        Represents a date and time value as specified by ISO 8601.
        Maps to the Python `datetime.datetime` type.
        """
    ),
    specified_by_url="https://datatracker.ietf.org/doc/html/rfc3339#section-5.6",
)

GraphQLDateTime = datetime_scalar.as_graphql_scalar()


@datetime_scalar.parse.register
def _(value: str) -> datetime.datetime:
    parsed_value: datetime.datetime | None = dateparse.parse_datetime(value)
    if parsed_value is None:
        raise GraphQLScalarInvalidValueError(typename="datetime")

    if settings.USE_TZ and is_naive(parsed_value):
        parsed_value = parsed_value.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
        parsed_value = parsed_value.astimezone(get_default_timezone())

    return parsed_value


@datetime_scalar.serialize.register
def _(value: str) -> str:
    parsed_value: datetime.datetime | None = dateparse.parse_datetime(value)
    if parsed_value is None:
        raise GraphQLScalarInvalidValueError(typename="datetime")

    if settings.USE_TZ and is_naive(parsed_value):
        parsed_value = parsed_value.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
        parsed_value = parsed_value.astimezone(get_default_timezone())

    return parsed_value.isoformat()


@datetime_scalar.serialize.register
def _(value: datetime.datetime) -> str:
    return value.isoformat()
