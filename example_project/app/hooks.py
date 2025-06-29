from __future__ import annotations

import datetime
import traceback
from typing import TYPE_CHECKING, Any

from undine.hooks import LifecycleHook

if TYPE_CHECKING:
    from collections.abc import Generator

    from graphql.pyutils import AwaitableOrValue

    from undine.utils.graphql.websocket import WebSocketRequest


class ExampleHook(LifecycleHook):
    def run(self) -> Generator[None, None, None]:
        yield


class ErrorLoggingHook(LifecycleHook):
    def run(self) -> Generator[None, None, None]:
        try:
            yield
        except Exception:
            print(traceback.format_exc())  # noqa: T201,RUF100
            raise


def ping_hook(request: WebSocketRequest) -> AwaitableOrValue[dict[str, Any] | None]:
    """Hook for custom ping logic."""
    timestamp = int(datetime.datetime.now(tz=datetime.UTC).timestamp() * 100_000)
    return {"timestamp": str(timestamp)}
