from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any

from undine.hooks import LifecycleHook

if TYPE_CHECKING:
    from collections.abc import Generator

    from graphql import GraphQLFieldResolver
    from graphql.pyutils import AwaitableOrValue

    from undine import GQLInfo
    from undine.utils.graphql.websocket import WebSocketRequest


logger = logging.getLogger(__name__)


class ExampleHook(LifecycleHook):
    def on_operation(self) -> Generator[None, None, None]:
        yield

    def on_parse(self) -> Generator[None, None, None]:
        yield

    def on_validation(self) -> Generator[None, None, None]:
        yield

    def on_execution(self) -> Generator[None, None, None]:
        yield


class ErrorLoggingMiddleware(LifecycleHook):
    def resolve(self, resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        try:
            return resolver(root, info, **kwargs)
        except Exception:
            logger.exception("Error occurred")
            raise


def ping_hook(request: WebSocketRequest) -> AwaitableOrValue[dict[str, Any] | None]:
    """Hook for custom ping logic."""
    timestamp = int(datetime.datetime.now(tz=datetime.UTC).timestamp() * 100_000)
    return {"timestamp": str(timestamp)}
