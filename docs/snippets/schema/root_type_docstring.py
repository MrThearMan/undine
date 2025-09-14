from undine import Entrypoint, RootType


class Query(RootType):
    """Operations for querying."""

    @Entrypoint
    def testing(self) -> str:
        return "Hello, World!"
