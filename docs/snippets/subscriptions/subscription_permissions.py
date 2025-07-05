import asyncio
from collections.abc import AsyncGenerator

from undine import Entrypoint, GQLInfo, RootType, create_schema
from undine.exceptions import GraphQLPermissionError


class Query(RootType):
    @Entrypoint
    def task(self, info: GQLInfo) -> str:
        return "Hello World"


class Subscription(RootType):
    @Entrypoint
    async def countdown(self, info: GQLInfo) -> AsyncGenerator[int, None]:
        for i in range(10, 0, -1):
            await asyncio.sleep(1)
            yield i

    @countdown.permissions
    def countdown_permissions(self, info: GQLInfo, value: int) -> None:
        if value > 10 and not info.context.user.is_superuser:
            msg = "Countdown value is too high"
            raise GraphQLPermissionError(msg)


schema = create_schema(query=Query, subscription=Subscription)
