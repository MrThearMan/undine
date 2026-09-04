from collections.abc import Generator
from typing import ClassVar

from undine.hooks import HookPriority, LifecycleHook


class RequestLoggingHook(LifecycleHook):
    """Runs outside every built-in hook, so it also sees the responses served from a cache."""

    priority: ClassVar[int] = HookPriority.TRACING - 10

    def on_operation(self) -> Generator[None, None, None]:
        yield
