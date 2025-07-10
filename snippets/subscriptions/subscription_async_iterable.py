import asyncio
from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator

from undine import Entrypoint, GQLInfo, RootType, create_schema


class Query(RootType):
    @Entrypoint
    def task(self, info: GQLInfo) -> str:
        return "Hello World"


class Countdown:
    def __aiter__(self) -> AsyncIterator[int]:
        return self.gen()

    async def gen(self) -> AsyncGenerator[int, None]:
        for i in range(10, 0, -1):
            await asyncio.sleep(1)
            yield i


class Subscription(RootType):
    @Entrypoint
    async def countdown(self, info: GQLInfo) -> AsyncIterable[int]:
        return Countdown()


schema = create_schema(query=Query, subscription=Subscription)
