from undine import Entrypoint, RootType, create_schema


class Query(RootType):
    @Entrypoint
    def testing(self) -> str:
        return "Hello, World!"


schema = create_schema(query=Query)
