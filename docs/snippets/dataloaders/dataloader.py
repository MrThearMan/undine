import asyncio
import datetime
from typing import TypedDict

import httpx

from undine import DataLoader, Entrypoint, GQLInfo, RootType


class Pet(TypedDict):
    name: str
    species: str
    breed: str
    birthday: datetime.date


async def load_pets(keys: list[str]) -> list[Pet]:
    tasks: list[asyncio.Task[httpx.Response]] = []

    async with httpx.AsyncClient() as client, asyncio.TaskGroup() as group:
        for key in keys:
            url = f"https://example.com/pets/{key}"
            task = group.create_task(client.get(url))
            tasks.append(task)

    # Validation skipped for brevity
    return [task.result().json() for task in tasks]


loader = DataLoader(load_fn=load_pets)


class Query(RootType):
    @Entrypoint
    async def pet_by_name(self, info: GQLInfo, name: str) -> Pet:
        return await loader.load(name)
