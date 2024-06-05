from __future__ import annotations

import uuid
from inspect import cleandoc

from ._definition import ScalarType

__all__ = [
    "GraphQLUUID",
    "uuid_scalar",
]


uuid_scalar: ScalarType[uuid.UUID, str] = ScalarType(
    name="UUID",
    description=cleandoc(
        """
        Represents a universally unique identifier string.
        Maps to Python's `uuid.UUID` type.
        """
    ),
    specified_by_url="https://datatracker.ietf.org/doc/html/rfc9562",
)

GraphQLUUID = uuid_scalar.as_graphql_scalar()


@uuid_scalar.parse.register
def _(value: str) -> uuid.UUID:
    return uuid.UUID(hex=value)


@uuid_scalar.parse.register
def _(value: int) -> uuid.UUID:
    return uuid.UUID(int=value)


@uuid_scalar.serialize.register
def _(value: str) -> str:
    return str(uuid.UUID(hex=value))


@uuid_scalar.serialize.register
def _(value: uuid.UUID) -> str:
    return str(value)


@uuid_scalar.serialize.register
def _(value: int) -> str:
    return str(uuid.UUID(int=value))


@uuid_scalar.serialize.register
def _(value: bytes) -> str:
    return str(uuid.UUID(bytes=value))
