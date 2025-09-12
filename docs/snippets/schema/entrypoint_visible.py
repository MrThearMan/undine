from undine import Entrypoint, RootType
from undine.typing import DjangoRequestProtocol


class Query(RootType):
    @Entrypoint
    def testing(self, name: str) -> str:
        return f"Hello, {name}!"

    @testing.visible
    def testing_visible(self, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser
