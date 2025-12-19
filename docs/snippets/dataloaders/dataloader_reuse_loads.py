from typing import TypedDict

from undine import DataLoader


class Pokemon(TypedDict): ...


async def load_pokemon(keys: list[str]) -> list[Pokemon]: ...


pokemon_loader = DataLoader(load_fn=load_pokemon, reuse_loads=False)
