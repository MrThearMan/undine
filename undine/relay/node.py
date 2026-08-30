from __future__ import annotations

from typing import TYPE_CHECKING, Unpack

from graphql import GraphQLID, GraphQLNonNull
from graphql.type.scalars import serialize_id

from undine import InterfaceField, InterfaceType
from undine.exceptions import InterfaceFieldNodeIDError

from .utils import decode_base64, encode_base64

if TYPE_CHECKING:
    from undine import Field
    from undine.typing import InterfaceFieldParams


__all__ = [
    "Node",
    "NodeIDField",
    "from_global_id",
    "to_global_id",
]


class NodeIDField(InterfaceField):
    """Field for the `Node` interface that converts primary key into string ID."""

    def __init__(self, **kwargs: Unpack[InterfaceFieldParams]) -> None:
        ref = GraphQLNonNull(GraphQLID)
        kwargs.setdefault("description", "The Global ID of an object.")
        kwargs.setdefault("field_name", "pk")
        super().__init__(ref, **kwargs)

    def check_inheritance(self, field: Field | InterfaceField) -> None:
        # Node ID is special, since it converts any type of primary key into string,
        # so we can assume that it will work even given any model pk type.
        #
        # Guard against interface inheritance losing this check override.
        if isinstance(field, InterfaceField) and not isinstance(field, NodeIDField):
            raise InterfaceFieldNodeIDError(interface=field.interface_type)


class Node(InterfaceType):
    """An interface for objects with Global IDs."""

    id = NodeIDField()


def to_global_id(typename: str, object_id: str | int) -> str:
    """
    Takes a typename and an object ID specific to that type,
    and returns a "Global ID" that is unique among all types.
    """
    return encode_base64(f"ID:{typename}:{serialize_id(object_id)}")


def from_global_id(global_id: str) -> tuple[str, str | int]:
    """
    Takes the "Global ID" created by `to_global_id`,
    and returns the typename and object ID used to create it.
    """
    global_id = decode_base64(global_id)
    _, typename, object_id = global_id.split(":")
    if object_id.isdigit():
        return typename, int(object_id)
    return typename, object_id
