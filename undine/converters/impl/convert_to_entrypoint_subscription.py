from __future__ import annotations

from inspect import isasyncgenfunction, iscoroutinefunction
from types import FunctionType
from typing import Any

from graphql import GraphQLFieldResolver

from undine import Entrypoint, InterfaceType, MutationType, QueryType, UnionType
from undine.converters import convert_to_entrypoint_subscription
from undine.relay import Connection, Node
from undine.resolvers import FunctionSubscriptionResolver


@convert_to_entrypoint_subscription.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLFieldResolver | None:
    if not isasyncgenfunction(ref) and not iscoroutinefunction(ref):
        return None

    # We don't know if the function submitted here is actually for a subscription,
    # or if it returns a something that can be used for subscriptions,
    # but there is no harm in creating the resolver anyway.
    caller: Entrypoint = kwargs["caller"]
    return FunctionSubscriptionResolver(func=ref, entrypoint=caller)


@convert_to_entrypoint_subscription.register
def _(
    _: type[QueryType | MutationType | UnionType | Node | InterfaceType] | Connection,
    **kwargs: Any,
) -> GraphQLFieldResolver | None:
    # Don't create a subscription resolver for any entrypoint reference that is not used for subscriptions
    return None
