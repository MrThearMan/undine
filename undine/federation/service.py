from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graphql import GraphQLNonNull

from undine.entrypoint import Entrypoint
from undine.federation.scalars import FederationServiceType
from undine.settings import undine_settings

if TYPE_CHECKING:
    from undine.entrypoint import RootType
    from undine.typing import GQLInfo

__all__ = [
    "make_service_entrypoint",
]


def _service_resolver(root: Any, info: GQLInfo) -> dict[str, str]:
    sdl = info.schema.extensions.get(undine_settings.FEDERATION_SDL_EXTENSIONS_KEY, "")
    return {"sdl": sdl}


def make_service_entrypoint(query: type[RootType]) -> Entrypoint:
    entrypoint = Entrypoint(
        GraphQLNonNull(FederationServiceType),
        schema_name="_service",
        extensions={undine_settings.FEDERATION_BUILTIN_EXTENSIONS_KEY: True},
    )
    entrypoint.resolve(_service_resolver)
    entrypoint.__connect__(query, "_service")
    return entrypoint
