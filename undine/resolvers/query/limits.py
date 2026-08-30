from __future__ import annotations

from typing import TYPE_CHECKING

from undine.settings import undine_settings
from undine.utils.graphql.utils import get_arguments

if TYPE_CHECKING:
    from undine import Entrypoint
    from undine.pagination import OffsetPagination, OffsetPaginationHandler
    from undine.typing import GQLInfo


__all__ = [
    "entrypoint_limit",
    "offset_pagination_handler",
]


def entrypoint_limit(entrypoint: Entrypoint) -> int | None:
    """
    The number of rows the entrypoint caps its result at. `None` if it is not capped.

    A paginated entrypoint returns the page its arguments ask for, so its limit does not apply.
    """
    if offset_pagination(entrypoint) is not None:
        return None
    return entrypoint.limit


def offset_pagination_handler(entrypoint: Entrypoint, info: GQLInfo) -> OffsetPaginationHandler | None:
    """The handler for the page the client asked for. `None` if the entrypoint is not offset paginated."""
    pagination = offset_pagination(entrypoint)
    if pagination is None:
        return None

    arguments = get_arguments(info)
    return pagination.pagination_handler(
        offset=arguments.get("offset"),
        limit=arguments.get("limit"),
        page_size=pagination.page_size,
    )


def offset_pagination(entrypoint: Entrypoint) -> OffsetPagination | None:
    key = undine_settings.OFFSET_PAGINATION_EXTENSIONS_KEY
    return entrypoint.extensions.get(key)
