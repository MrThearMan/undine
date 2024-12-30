from __future__ import annotations

from types import FunctionType
from typing import TYPE_CHECKING, Any

from graphql import GraphQLFieldResolver

from undine.resolvers import (
    BulkCreateResolver,
    BulkDeleteResolver,
    BulkUpdateResolver,
    ConnectionResolver,
    CreateResolver,
    CustomResolver,
    DeleteResolver,
    FunctionResolver,
    NodeResolver,
    QueryTypeManyResolver,
    QueryTypeSingleResolver,
    UpdateResolver,
)
from undine.typing import EntrypointRef
from undine.utils.function_dispatcher import FunctionDispatcher

if TYPE_CHECKING:
    from undine import Entrypoint

__all__ = [
    "convert_entrypoint_ref_to_resolver",
]


convert_entrypoint_ref_to_resolver = FunctionDispatcher[EntrypointRef, GraphQLFieldResolver]()
"""
Convert the Undine Entrypoint reference to a GraphQL field resolver.

Positional arguments:
 - ref: The reference to convert.

Keyword arguments:
 - caller: The 'undine.Entrypoint' instance that is calling this function.
"""


@convert_entrypoint_ref_to_resolver.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLFieldResolver:
    return FunctionResolver(ref)


def load_deferred_converters() -> None:  # noqa: C901
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation.
    from undine import MutationType, QueryType
    from undine.relay import Connection, Node

    @convert_entrypoint_ref_to_resolver.register
    def _(ref: type[QueryType], **kwargs: Any) -> GraphQLFieldResolver:
        caller: Entrypoint = kwargs["caller"]
        if caller.many:
            return QueryTypeManyResolver(query_type=ref, max_complexity=caller.max_complexity)
        return QueryTypeSingleResolver(query_type=ref, max_complexity=caller.max_complexity)

    @convert_entrypoint_ref_to_resolver.register
    def _(ref: type[MutationType], **kwargs: Any) -> GraphQLFieldResolver:  # noqa: PLR0911
        # TODO: Optimize queries from mutations.
        caller: Entrypoint = kwargs["caller"]
        if caller.many:
            if ref.__mutation_kind__ == "create":
                return BulkCreateResolver(mutation_type=ref)
            if ref.__mutation_kind__ == "update":
                return BulkUpdateResolver(mutation_type=ref)
            if ref.__mutation_kind__ == "delete":
                return BulkDeleteResolver(mutation_type=ref)
            return CustomResolver(mutation_type=ref)

        if ref.__mutation_kind__ == "create":
            return CreateResolver(mutation_type=ref)
        if ref.__mutation_kind__ == "update":
            return UpdateResolver(mutation_type=ref)
        if ref.__mutation_kind__ == "delete":
            return DeleteResolver(mutation_type=ref)
        return CustomResolver(mutation_type=ref)

    @convert_entrypoint_ref_to_resolver.register
    def _(ref: Connection, **kwargs: Any) -> GraphQLFieldResolver:
        caller: Entrypoint = kwargs["caller"]
        return ConnectionResolver(connection=ref, max_complexity=caller.max_complexity)

    @convert_entrypoint_ref_to_resolver.register
    def _(_: Node, **kwargs: Any) -> GraphQLFieldResolver:
        return NodeResolver()
