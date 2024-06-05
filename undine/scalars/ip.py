from __future__ import annotations

from django.core.validators import validate_ipv46_address

from ._definition import ScalarType

__all__ = [
    "GraphQLIP",
    "ip_scalar",
]


ip_scalar: ScalarType[str, str] = ScalarType(
    name="IP",
    description="Represents a valid IPv4 or IPv6 address.",
    specified_by_url="https://datatracker.ietf.org/doc/html/rfc8200",
)

GraphQLIP = ip_scalar.as_graphql_scalar()


@ip_scalar.serialize.register
@ip_scalar.parse.register
def _(value: str) -> str:
    validate_ipv46_address(value)
    return value
