from typing import Self


class Base:
    def format_common_iso(self) -> str: ...

    @classmethod
    def parse_common_iso(cls, value: str) -> Self: ...


class Instant(Base): ...


class ZonedDateTime(Base): ...


class PlainDateTime(Base): ...
