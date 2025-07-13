from collections.abc import AsyncGenerator, Generator

from undine.hooks import LifecycleHook


class ExampleHook(LifecycleHook):
    def run(self) -> Generator[None, None, None]:
        print("before")
        yield
        print("after")

    async def run_async(self) -> AsyncGenerator[None, None]:
        print("before async")
        yield
        print("after async")
