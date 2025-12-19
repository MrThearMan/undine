from asyncio import Future
from typing import TypedDict

from undine import DataLoader, Entrypoint, GQLInfo, RootType


class Pokemon(TypedDict):
    id: int
    name: str
    height: int
    weight: int


async def load_pokemon(keys: list[str]) -> list[Pokemon]: ...


pokemon_loader = DataLoader(load_fn=load_pokemon)

pikachu = Pokemon(
    id=25,
    name="pikachu",
    height=4,
    weight=60,
)


class Query(RootType):
    @Entrypoint
    def pokemon_by_name(self, info: GQLInfo, name: str) -> Future[Pokemon]:
        return pokemon_loader.prime(key="pikachu", value=pikachu).load(name)
