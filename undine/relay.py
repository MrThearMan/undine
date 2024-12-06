from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any

from graphql import (
    GraphQLArgument,
    GraphQLArgumentMap,
    GraphQLBoolean,
    GraphQLError,
    GraphQLField,
    GraphQLID,
    GraphQLInt,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLOutputType,
    GraphQLString,
)

from undine.converters import convert_entrypoint_ref_to_resolver, convert_to_graphql_argument_map
from undine.optimizer.ast import get_underlying_type
from undine.pagination import calculate_queryset_slice, validate_pagination_args
from undine.settings import undine_settings
from undine.utils.graphql import get_or_create_object_type

if TYPE_CHECKING:
    from undine import Field, QueryType
    from undine.typing import GQLInfo


__all__ = [
    "Connection",
]


def encode_cursor(string: str) -> str:
    return base64.b64encode(string.encode("utf-8")).decode("ascii")


def decode_cursor(string: str) -> str:
    return base64.b64decode(string.encode("ascii")).decode("utf-8")


PREFIX = "arrayconnection:"


def offset_to_cursor(offset: int) -> str:
    """Create the cursor string from an offset."""
    return encode_cursor(f"{PREFIX}{offset}")


def cursor_to_offset(cursor: str) -> int:
    """Extract the offset from the cursor string."""
    return int(decode_cursor(cursor).removeprefix(PREFIX))


def to_global_id(typename: str, object_id: str | int) -> str:
    """
    Takes a typename and an object ID specific to that type,
    and returns a "Global ID" that is unique among all types.
    """
    return encode_cursor(f"{typename}:{GraphQLID.serialize(object_id)}")


def from_global_id(global_id: str) -> tuple[str, str | int]:
    """
    Takes the "Global ID" created by `to_global_id`,
    and returns the typename and object ID used to create it.
    """
    global_id = decode_cursor(global_id)
    typename, object_id = global_id.split(":", 1)
    if object_id.isdigit():
        object_id = int(object_id)
    return typename, object_id


PageInfoType = GraphQLObjectType(
    name="PageInfo",
    description="Information about pagination in a connection.",
    fields={
        "hasNextPage": GraphQLField(
            GraphQLNonNull(GraphQLBoolean),
            description="When paginating forwards, are there more items?",
        ),
        "hasPreviousPage": GraphQLField(
            GraphQLNonNull(GraphQLBoolean),
            description="When paginating backwards, are there more items?",
        ),
        "startCursor": GraphQLField(
            GraphQLString,  # null if no results
            description="When paginating backwards, the cursor to continue.",
        ),
        "endCursor": GraphQLField(
            GraphQLString,  # null if no results
            description="When paginating forwards, the cursor to continue.",
        ),
    },
)


class GlobalID:
    def __init__(self, typename: str) -> None:
        self.typename = typename

    def resolver(self, root: Any, info: GQLInfo, **kwargs: Any) -> str:
        return to_global_id(self.typename, root.pk)


class Node:
    interface = GraphQLInterfaceType(
        name="Node",
        description="An object with an ID",
        fields={
            "id": GraphQLField(
                GraphQLNonNull(GraphQLID),
                description="The ID of an object",
            ),
        },
    )

    arguments = {
        "id": GraphQLArgument(
            GraphQLNonNull(GraphQLID),
            description="The ID of an object",
        ),
    }

    @classmethod
    def resolver(cls, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        typename, object_id = from_global_id(kwargs["id"])

        object_type = info.schema.get_type(typename)
        if object_type is None:
            msg = f"Object type '{typename}' does not exist in schema."
            raise GraphQLError(msg)

        query_type: type[QueryType] | None = object_type.extensions.get(undine_settings.QUERY_TYPE_EXTENSIONS_KEY)
        if query_type is None:
            msg = f"Cannot find undine QueryType from object type '{typename}'."
            raise GraphQLError(msg)

        field: Field | None = query_type.__field_map__.get("id")
        if field is None:
            msg = f"The object type '{typename}' doesn't have an 'id' field."
            raise GraphQLError(msg)

        field_type = get_underlying_type(field.get_field_type())
        if field_type is not GraphQLID:
            msg = (
                f"The 'id' field of the object type '{typename}' must be of type '{GraphQLID.name}' "
                f"to comply with the {cls.__name__} interface."
            )
            raise GraphQLError(msg)

        resolver = convert_entrypoint_ref_to_resolver(query_type, many=False)
        return resolver(root, info, pk=object_id)


class Connection:
    def __init__(self, query_type: type[QueryType], *, max_limit: int | None = 100) -> None:
        self.query_type = query_type
        self.max_limit = max_limit

        self.query_type_resolver = convert_entrypoint_ref_to_resolver(query_type, many=True)
        self.query_type_arguments = convert_to_graphql_argument_map(query_type, many=True, entrypoint=True)

    def output_type(self) -> GraphQLOutputType:
        return get_or_create_object_type(
            name=self.query_type.__typename__ + "Connection",
            description="A connection to a list of items.",
            fields={
                "totalCount": GraphQLField(
                    GraphQLNonNull(GraphQLInt),
                    description="Total number of items in the connection.",
                ),
                "pageInfo": GraphQLField(
                    GraphQLNonNull(PageInfoType),
                    description="Information to aid in pagination.",
                ),
                "edges": GraphQLField(
                    GraphQLList(
                        GraphQLObjectType(
                            name=self.query_type.__typename__ + "Edge",
                            description="An edge in a connection.",
                            fields=lambda: {
                                "cursor": GraphQLField(
                                    GraphQLNonNull(GraphQLString),
                                    description="A cursor for use in pagination",
                                ),
                                "node": GraphQLField(
                                    self.query_type.__output_type__(),
                                    description="The item at the end of the edge",
                                ),
                            },
                        ),
                    ),
                    description="A list of edges.",
                ),
            },
        )

    def arguments(self) -> GraphQLArgumentMap:
        return {
            "after": GraphQLArgument(
                GraphQLString,
                description="Returns the items in the list that come after the specified cursor.",
                out_name="after",
            ),
            "first": GraphQLArgument(
                GraphQLInt,
                description="Returns the first n items from the list.",
                out_name="first",
            ),
            "before": GraphQLArgument(
                GraphQLString,
                description="Returns the items in the list that come before the specified cursor.",
                out_name="before",
            ),
            "last": GraphQLArgument(
                GraphQLInt,
                description="Returns the last n items from the list.",
                out_name="last",
            ),
            "offset": GraphQLArgument(
                GraphQLInt,
                description="Offset for the connection.",
                out_name="offset",
            ),
            **self.query_type_arguments,
        }

    def resolver(self, root: Any, info: GQLInfo, **kwargs: Any) -> dict[str, Any]:
        pagination_args = validate_pagination_args(
            first=kwargs.pop("first", None),
            last=kwargs.pop("last", None),
            offset=kwargs.pop("offset", None),
            after=kwargs.pop("after", None),
            before=kwargs.pop("before", None),
            max_limit=self.max_limit,
        )

        queryset = self.query_type_resolver(root, info, **kwargs)

        pagination_args.size = total_count = queryset.count()

        cut = calculate_queryset_slice(pagination_args=pagination_args)

        queryset = queryset[cut]

        edges = [
            {
                "cursor": offset_to_cursor(cut.start + index),
                "node": instance,
            }
            for index, instance in enumerate(queryset)
        ]
        return {
            "totalCount": total_count,
            "pageInfo": {
                "hasNextPage": cut.stop < total_count,
                "hasPreviousPage": cut.start > 0,
                "startCursor": None if not edges else edges[0]["cursor"],
                "endCursor": None if not edges else edges[-1]["cursor"],
            },
            "edges": edges,
        }
