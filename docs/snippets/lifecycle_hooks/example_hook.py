from collections.abc import Generator

from undine.hooks import LifecycleHook


class ExampleHook(LifecycleHook):
    def run(self) -> Generator[None, None, None]:
        print("before")
        yield
        print("after")
