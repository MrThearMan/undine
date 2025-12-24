from collections.abc import AsyncGenerator, Generator

from undine.hooks import LifecycleHook


class ExampleHook(LifecycleHook):
    """Example hook"""

    def on_parse(self) -> Generator[None, None, None]:
        print("before")
        yield
        print("after")

    # Async hook uses synchronous version if not implemented.
    async def on_parse_async(self) -> AsyncGenerator[None, None]:
        print("before async")
        yield
        print("after async")
