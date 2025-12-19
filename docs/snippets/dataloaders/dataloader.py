import asyncio
from asyncio import Future
from typing import TypedDict

import httpx

from undine import DataLoader, Entrypoint, GQLInfo, RootType


class Pokemon(TypedDict):
    id: int
    name: str
    height: int
    weight: int


async def load_pokemon(keys: list[str]) -> list[Pokemon]:
    base_url = "https://pokeapi.co/api/v2/pokemon/{pokemon_name}"

    async with httpx.AsyncClient() as client:
        requests = (client.get(base_url.format(pokemon_name=key)) for key in keys)
        responses = await asyncio.gather(*requests)

    # Validation skipped for brevity
    return [response.json() for response in responses]


pokemon_loader = DataLoader(load_fn=load_pokemon)


class Query(RootType):
    @Entrypoint
    def pokemon_by_name(self, info: GQLInfo, name: str) -> Future[Pokemon]:
        return pokemon_loader.load(name)
