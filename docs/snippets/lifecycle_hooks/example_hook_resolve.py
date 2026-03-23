from collections.abc import Awaitable
from typing import Any

from graphql import GraphQLFieldResolver
from graphql.pyutils import AwaitableOrValue

from undine import GQLInfo
from undine.hooks import LifecycleHook


class ExampleHook(LifecycleHook):
    """Example hook"""

    # The 'resolve' step only has a synchronous interface.
    # If you want your hook to also support awaitable resolvers,
    # you need to check if the resolver returns an awaitable and handle it separately.

    def resolve(self, resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[Any]:
        print("before")
        result = resolver(root, info, **kwargs)
        print("after")

        if info.is_awaitable(result):
            return self.resolve_async(resolver=result, root=root, info=info, **kwargs)

        return result

    async def resolve_async(self, awaitable: Awaitable[Any], root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        print("before async")
        result = await awaitable
        print("after async")
        return result
