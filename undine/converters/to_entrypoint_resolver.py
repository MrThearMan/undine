from __future__ import annotations

from types import FunctionType
from typing import Any

from graphql import GraphQLFieldResolver

from undine.resolvers import CreateResolver, CustomResolver, DeleteResolver, FunctionResolver, UpdateResolver
from undine.typing import EntrypointRef
from undine.utils.function_dispatcher import FunctionDispatcher

__all__ = [
    "convert_entrypoint_ref_to_resolver",
]


convert_entrypoint_ref_to_resolver = FunctionDispatcher[EntrypointRef, GraphQLFieldResolver]()
"""
Convert the Undine Entrypoint reference to a GraphQL field resolver.

:param ref: The reference to convert.
:param many: Whether the entrypoint is for a list field.
"""


@convert_entrypoint_ref_to_resolver.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLFieldResolver:
    return FunctionResolver.adapt(ref)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation.
    from undine.mutation import MutationType
    from undine.query import QueryType

    @convert_entrypoint_ref_to_resolver.register
    def _(ref: type[QueryType], **kwargs: Any) -> GraphQLFieldResolver:
        many: bool = kwargs["many"]
        return ref.__resolve_many__ if many else ref.__resolve_one__

    @convert_entrypoint_ref_to_resolver.register
    def _(ref: type[MutationType], **kwargs: Any) -> GraphQLFieldResolver:
        if ref.__mutation_kind__ == "create":
            return CreateResolver(mutation_type=ref)
        if ref.__mutation_kind__ == "update":
            return UpdateResolver(mutation_type=ref)
        if ref.__mutation_kind__ == "delete":
            return DeleteResolver(mutation_type=ref)
        return CustomResolver(mutation_type=ref)
