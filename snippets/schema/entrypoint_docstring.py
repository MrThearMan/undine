from undine import Entrypoint, RootType


class Query(RootType):
    @Entrypoint
    def testing(self, name: str) -> str:
        """
        Return a greeting.

        :param name: The name to greet.
        """
        return f"Hello, {name}!"
