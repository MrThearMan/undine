from __future__ import annotations

from django.core.validators import validate_ipv4_address

from ._definition import ScalarType

__all__ = [
    "GraphQLIPv4",
    "ipv4_scalar",
]


ipv4_scalar: ScalarType[str, str] = ScalarType(
    name="IPv4",
    description="Represents a valid IPv4 address.",
    specified_by_url="https://datatracker.ietf.org/doc/html/rfc791",
)

GraphQLIPv4 = ipv4_scalar.as_graphql_scalar()


@ipv4_scalar.serialize.register
@ipv4_scalar.parse.register
def _(value: str) -> str:
    validate_ipv4_address(value)
    return value
