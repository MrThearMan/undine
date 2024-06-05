from __future__ import annotations

from django.core.validators import validate_ipv6_address

from ._definition import ScalarType

__all__ = [
    "GraphQLIPv6",
    "ipv6_scalar",
]


ipv6_scalar: ScalarType[str, str] = ScalarType(
    name="IPv6",
    description="Represents a valid IPv6 address.",
    specified_by_url="https://datatracker.ietf.org/doc/html/rfc8200",
)

GraphQLIPv6 = ipv6_scalar.as_graphql_scalar()


@ipv6_scalar.serialize.register
@ipv6_scalar.parse.register
def _(value: str) -> str:
    validate_ipv6_address(value)
    return value
