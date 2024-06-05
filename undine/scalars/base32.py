from __future__ import annotations

import base64

from ._definition import ScalarType

__all__ = [
    "GraphQLBase32",
    "base32_scalar",
]


base32_scalar: ScalarType[str, str] = ScalarType(
    name="Base32",
    description="Represents a base32-encoded string.",
    specified_by_url="https://datatracker.ietf.org/doc/html/rfc4648#section-6",
)

GraphQLBase32 = base32_scalar.as_graphql_scalar()


@base32_scalar.serialize.register
@base32_scalar.parse.register
def _(value: str) -> str:
    # Validate string is base32 encoded
    base64.b32decode(value.encode(encoding="utf-8")).decode(encoding="utf-8")
    return value


@base32_scalar.serialize.register
def _(value: bytes) -> str:
    # Validate string is base32 encoded
    base64.b32decode(value).decode(encoding="utf-8")
    return value.decode(encoding="utf-8")
