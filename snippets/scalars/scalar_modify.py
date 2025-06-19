from whenever import Instant, PlainDateTime, ZonedDateTime

from undine.scalars.datetime import datetime_scalar


@datetime_scalar.parse.register
def _(value: str) -> ZonedDateTime:
    # Default "str" parse overridden to use 'whenever'
    return ZonedDateTime.parse_common_iso(value)


@datetime_scalar.serialize.register
def _(value: Instant | ZonedDateTime | PlainDateTime) -> str:
    # Extend serialization with types from 'whenever'.
    # Same implementation for all types in the union
    return value.format_common_iso()
