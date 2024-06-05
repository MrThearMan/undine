from __future__ import annotations

from typing import TYPE_CHECKING

from undine.hooks import LifecycleHook

if TYPE_CHECKING:
    from collections.abc import Generator


class ExampleHook(LifecycleHook):
    def run(self) -> Generator[None, None, None]:
        yield
