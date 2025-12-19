from asyncio import Future
from typing import TypedDict

from undine import DataLoader, Entrypoint, GQLInfo, RootType


class Pokemon(TypedDict): ...


async def load_pokemon(keys: list[dict[str, str]]) -> list[Pokemon]: ...


def key_hash_fn(key: dict[str, str]) -> str:
    return key["name"]


pokemon_loader = DataLoader(load_fn=load_pokemon, key_hash_fn=key_hash_fn)


class Query(RootType):
    @Entrypoint
    def pokemon_by_name(self, info: GQLInfo, name: str) -> Future[Pokemon]:
        return pokemon_loader.load({"name": name})
