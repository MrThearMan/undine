from undine import Entrypoint, RootType


class Query(RootType, schema_name="MyQuery"):
    @Entrypoint
    def testing(self) -> str:
        return "Hello, World!"
