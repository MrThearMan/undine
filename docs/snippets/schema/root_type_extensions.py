from undine import Entrypoint, RootType


class Query(RootType, extensions={"foo": "bar"}):
    @Entrypoint
    def testing(self) -> str:
        return "Hello, World!"
