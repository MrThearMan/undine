from undine import Entrypoint, RootType


class Query(RootType):
    @Entrypoint
    def testing(self, name: str | None = None) -> str:
        return f"Hello, {name or 'World'}!"
