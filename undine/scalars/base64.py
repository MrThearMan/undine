from __future__ import annotations

import base64

from ._definition import ScalarType

__all__ = [
    "GraphQLBase64",
    "base64_scalar",
]


base64_scalar: ScalarType[str, str] = ScalarType(
    name="Base64",
    description="Represents a base64-encoded string.",
    specified_by_url="https://datatracker.ietf.org/doc/html/rfc4648#section-4",
)

GraphQLBase64 = base64_scalar.as_graphql_scalar()


@base64_scalar.serialize.register
@base64_scalar.parse.register
def _(value: str) -> str:
    # Validate string is base64 encoded
    base64.b64decode(value.encode(encoding="utf-8")).decode(encoding="utf-8")
    return value


@base64_scalar.serialize.register
def _(value: bytes) -> str:
    # Validate string is base64 encoded
    base64.b64decode(value).decode(encoding="utf-8")
    return value.decode(encoding="utf-8")
