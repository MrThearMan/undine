from __future__ import annotations

from inspect import isasyncgenfunction, iscoroutinefunction
from types import FunctionType
from typing import Any

from graphql import GraphQLFieldResolver

from undine import Entrypoint
from undine.converters import convert_to_entrypoint_subscription
from undine.resolvers import FunctionSubscriptionResolver
from undine.resolvers.subscription import ModelDeleteSubscriptionResolver, ModelSaveSubscriptionResolver
from undine.subscriptions import ModelDeleteSubscription, ModelSaveSubscription


@convert_to_entrypoint_subscription.register
def _(_: Any, **kwargs: Any) -> GraphQLFieldResolver | None:
    # Don't create a subscription resolver for any Entrypoint reference that is not used for subscriptions
    return None


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
def _(ref: ModelSaveSubscription, **kwargs: Any) -> GraphQLFieldResolver | None:
    caller: Entrypoint = kwargs["caller"]
    return ModelSaveSubscriptionResolver(subscription=ref, entrypoint=caller)


@convert_to_entrypoint_subscription.register
def _(ref: ModelDeleteSubscription, **kwargs: Any) -> GraphQLFieldResolver | None:
    caller: Entrypoint = kwargs["caller"]
    return ModelDeleteSubscriptionResolver(subscription=ref, entrypoint=caller)
