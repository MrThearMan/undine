import asyncio
from collections.abc import AsyncIterable

from undine import Entrypoint, Field, GQLInfo, QueryType, RootType, create_schema

from .models import Task


class TaskType(QueryType[Task]):
    id = Field()
    name = Field()
    done = Field()

    @Field
    async def slow(self, info: GQLInfo) -> str:
        await asyncio.sleep(5)
        return "OK"

    @Field
    async def countdown(self, info: GQLInfo) -> AsyncIterable[int]:
        for index in range(10, -1, -1):
            await asyncio.sleep(1)
            yield index


class Query(RootType):
    tasks = Entrypoint(TaskType, many=True)


schema = create_schema(query=Query)
