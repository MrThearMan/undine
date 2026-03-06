from undine import Entrypoint, RootType


class Query(RootType):
    @Entrypoint(cache_for_seconds=60)
    def testing(self, name: str) -> str:
        return f"Hello, {name}!"
