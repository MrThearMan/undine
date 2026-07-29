from undine import Entrypoint, RootType
from undine.typing import DjangoRequestProtocol


class Mutation(RootType):
    @Entrypoint
    def testing(self, name: str) -> str:
        return f"Hello, {name}!"

    @classmethod
    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        return request.user.is_authenticated
