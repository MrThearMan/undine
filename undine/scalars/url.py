from __future__ import annotations

from undine.utils.validators import validate_url

from ._definition import ScalarType

__all__ = [
    "GraphQLURL",
    "url_scalar",
]


url_scalar: ScalarType[str, str] = ScalarType(
    name="URL",
    description="Represents a valid URL.",
    specified_by_url="https://datatracker.ietf.org/doc/html/rfc3986",
)

GraphQLURL = url_scalar.as_graphql_scalar()


@url_scalar.serialize.register
@url_scalar.parse.register
def _(value: str) -> str:
    validate_url(value)
    return value
