from undine.federation import FederationField, FederationType, KeyDirective
from undine.typing import DjangoRequestProtocol


@KeyDirective(fields="id")
class UserExtension(FederationType, schema_name="User"):
    id = FederationField(int)

    @classmethod
    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        return request.user.is_authenticated
