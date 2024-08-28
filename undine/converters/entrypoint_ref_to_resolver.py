from __future__ import annotations

from types import FunctionType
from typing import Any

from graphql import GraphQLFieldResolver

from undine.typing import EntrypointRef
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.resolvers import MutationResolver, function_field_resolver

__all__ = [
    "convert_entrypoint_ref_to_resolver",
]


convert_entrypoint_ref_to_resolver = TypeDispatcher[EntrypointRef, GraphQLFieldResolver]()


@convert_entrypoint_ref_to_resolver.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLFieldResolver:
    return function_field_resolver(ref)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine import ModelGQLMutation, ModelGQLType

    @convert_entrypoint_ref_to_resolver.register
    def _(ref: type[ModelGQLType], **kwargs: Any) -> GraphQLFieldResolver:
        many: bool = kwargs["many"]
        return ref.__resolve_many__ if many else ref.__resolve_one__

    @convert_entrypoint_ref_to_resolver.register
    def _(ref: type[ModelGQLMutation], **kwargs: Any) -> GraphQLFieldResolver:
        if ref.__mutation_kind__ == "create":
            return MutationResolver(func=ref.__create_mutation__)
        if ref.__mutation_kind__ == "update":
            return MutationResolver(func=ref.__update_mutation__)
        if ref.__mutation_kind__ == "update":
            return MutationResolver(func=ref.__delete_mutation__)
        return MutationResolver(func=ref.__custom_mutation__)
