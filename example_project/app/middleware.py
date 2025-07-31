from __future__ import annotations

import logging
import traceback
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from graphql import GraphQLFieldResolver

    from undine.typing import GQLInfo


logger = logging.getLogger(__name__)


# Example function middleware
def error_logging_middleware(resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
    try:
        return resolver(root, info, **kwargs)
    except Exception:
        logger.exception(traceback.format_exc())
        raise


# Example class middleware
class ErrorLoggingMiddleware:
    @staticmethod
    def resolve(resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        try:
            return resolver(root, info, **kwargs)
        except Exception as err:
            logger.exception("Error occurred")
            return err
