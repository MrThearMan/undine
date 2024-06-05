from __future__ import annotations

from django.core.validators import validate_email

from ._definition import ScalarType

__all__ = [
    "GraphQLEmail",
    "email_scalar",
]


email_scalar: ScalarType[str, str] = ScalarType(
    name="Email",
    description="Represents a valid email address.",
    specified_by_url="https://datatracker.ietf.org/doc/html/rfc5322#section-3.4.1",
)

GraphQLEmail = email_scalar.as_graphql_scalar()


@email_scalar.serialize.register
@email_scalar.parse.register
def _(value: str) -> str:
    validate_email(value)
    return value
