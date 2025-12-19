from asyncio import Future
from typing import TypedDict

from undine import DataLoader, Entrypoint, GQLInfo, RootType


class Pokemon(TypedDict): ...


async def load_pokemon(keys: list[str]) -> list[Pokemon]: ...


pokemon_loader = DataLoader(load_fn=load_pokemon)


class Query(RootType):
    @Entrypoint
    def pokemon_by_name(self, info: GQLInfo, name: str) -> Future[Pokemon]:
        return pokemon_loader.clear(key=name).load(name)
