from typing import Any

from graphql import GraphQLFieldResolver

from undine import GQLInfo
from undine.hooks import LifecycleHook


class ExampleHook(LifecycleHook):
    """Example hook"""

    # The 'resolve' hook only has a synchronous interface.
    def resolve(self, resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        print("before")
        result = resolver(root, info, **kwargs)
        print("after")
        return result
