from pathlib import Path

from undine import Entrypoint, RootType, create_schema


class Query(RootType):
    @Entrypoint
    def testing(self) -> str:
        return "Hello, World!"


class Mutation(RootType):
    @Entrypoint
    def testing(self) -> int:
        return Path("foo.txt").write_text("Hello, World!", encoding="utf-8")


schema = create_schema(query=Query, mutation=Mutation)
