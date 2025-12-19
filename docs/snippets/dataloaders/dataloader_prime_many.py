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


async def load_pokemon_by_id(keys: list[int]) -> list[Pokemon]:
    base_url = "https://pokeapi.co/api/v2/pokemon/{pokemon_id}"

    async with httpx.AsyncClient() as client:
        requests = (client.get(base_url.format(pokemon_id=key)) for key in keys)
        responses = await asyncio.gather(*requests)

    # Validation skipped for brevity
    data: list[Pokemon] = [response.json() for response in responses]

    # Prime the name loader with the fetched data
    names = [pokemon["name"] for pokemon in data]
    pokemon_name_loader.prime_many(keys=names, values=data, can_prime_pending_loads=True)
    return data


async def load_pokemon_by_name(keys: list[str]) -> list[Pokemon]:
    base_url = "https://pokeapi.co/api/v2/pokemon/{pokemon_name}"

    async with httpx.AsyncClient() as client:
        requests = (client.get(base_url.format(pokemon_name=key)) for key in keys)
        responses = await asyncio.gather(*requests)

    # Validation skipped for brevity
    data: list[Pokemon] = [response.json() for response in responses]

    # Prime the ID loader with the fetched data
    ids = [pokemon["id"] for pokemon in data]
    pokemon_id_loader.prime_many(keys=ids, values=data, can_prime_pending_loads=True)
    return data


lock = asyncio.Lock()
pokemon_id_loader = DataLoader(load_fn=load_pokemon_by_id, lock=lock)
pokemon_name_loader = DataLoader(load_fn=load_pokemon_by_name, lock=lock)


class Query(RootType):
    @Entrypoint
    def pokemon_by_id(self, info: GQLInfo, id: int) -> Future[Pokemon]:
        return pokemon_id_loader.load(id)

    @Entrypoint
    def pokemon_by_name(self, info: GQLInfo, name: str) -> Future[Pokemon]:
        return pokemon_name_loader.load(name)
