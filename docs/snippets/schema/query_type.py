from undine import Entrypoint, GQLInfo, RootType


class Query(RootType):
    @Entrypoint
    def testing(self, info: GQLInfo) -> str:
        return "Hello World!"
