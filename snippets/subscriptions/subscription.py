import asyncio
from collections.abc import AsyncGenerator

from undine import Entrypoint, GQLInfo, RootType, create_schema


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


schema = create_schema(query=Query, subscription=Subscription)
