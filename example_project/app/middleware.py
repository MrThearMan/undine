from __future__ import annotations

import logging
import traceback
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from graphql import GraphQLFieldResolver

    from undine.typing import GQLInfo


logger = logging.getLogger(__name__)


def error_logging_middleware(resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
    try:
        return resolver(root, info, **kwargs)
    except Exception:
        logger.exception(traceback.format_exc())
        raise
