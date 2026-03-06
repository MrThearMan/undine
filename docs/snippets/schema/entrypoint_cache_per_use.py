from undine import Entrypoint, RootType


class Query(RootType):
    @Entrypoint(cache_for_seconds=60, cache_per_user=True)
    def testing(self, name: str) -> str:
        return f"Hello, {name}!"
