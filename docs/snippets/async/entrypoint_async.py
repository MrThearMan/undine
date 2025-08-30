from undine import Entrypoint, GQLInfo, RootType


class Query(RootType):
    @Entrypoint
    async def example(self, info: GQLInfo) -> str:
        return "foo"

    @example.permissions
    async def permissions(self, info: GQLInfo, value: str) -> None:
        # Some permission check logic here
        return
