from undine import Entrypoint, RootType


class Query(RootType):
    @Entrypoint
    def testing(self, name: str) -> str:
        return f"Hello, {name}!"
