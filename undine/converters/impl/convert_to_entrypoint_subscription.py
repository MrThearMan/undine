from __future__ import annotations

from types import FunctionType
from typing import Any

from graphql import GraphQLFieldResolver

from undine import Entrypoint
from undine.converters import convert_to_entrypoint_subscription
from undine.resolvers.subscription import EntrypointFunctionSubscription


@convert_to_entrypoint_subscription.register
def _(_: Any, **kwargs: Any) -> GraphQLFieldResolver | None:  # TODO: Test
    return None


@convert_to_entrypoint_subscription.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLFieldResolver | None:  # TODO: Test
    caller: Entrypoint = kwargs["caller"]
    # TODO: Different resolvers for AsyncGenerator / AsyncIterator / AsyncIterable
    return EntrypointFunctionSubscription(func=ref, entrypoint=caller)
