"""GraphQL execution middleware."""

import traceback
from typing import Any

from graphql import GraphQLFieldResolver

from undine.typing import GQLInfo
from undine.utils.logging import undine_logger

__all__ = [
    "error_logging_middleware",
]


def error_logging_middleware(resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
    try:
        return resolver(root, info, **kwargs)
    except Exception as err:  # noqa: BLE001
        undine_logger.error(traceback.format_exc())
        return err
