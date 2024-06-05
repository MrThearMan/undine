from __future__ import annotations

from inspect import cleandoc

from ._definition import ScalarType

__all__ = [
    "GraphQLNull",
    "null_scalar",
]


null_scalar: ScalarType[None, None] = ScalarType(
    name="Null",
    description=cleandoc(
        """
        Represents represents an always null value.
        Maps to the Python `None` value.
        """
    ),
)

GraphQLNull = null_scalar.as_graphql_scalar()


@null_scalar.serialize.register
@null_scalar.parse.register
def _(value: None) -> None:
    return value
