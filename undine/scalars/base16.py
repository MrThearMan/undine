from __future__ import annotations

import base64

from ._definition import ScalarType

__all__ = [
    "GraphQLBase16",
    "base16_scalar",
]


base16_scalar: ScalarType[str, str] = ScalarType(
    name="Base16",
    description="Represents a base16-encoded string.",
    specified_by_url="https://datatracker.ietf.org/doc/html/rfc4648#section-8",
)

GraphQLBase16 = base16_scalar.as_graphql_scalar()


@base16_scalar.serialize.register
@base16_scalar.parse.register
def _(value: str) -> str:
    # Validate string is base16 encoded
    base64.b16decode(value.encode(encoding="utf-8")).decode(encoding="utf-8")
    return value


@base16_scalar.serialize.register
def _(value: bytes) -> str:
    # Validate string is base16 encoded
    base64.b16decode(value).decode(encoding="utf-8")
    return value.decode(encoding="utf-8")
