from undine.federation import FederationField, FederationType, KeyDirective
from undine.typing import DjangoRequestProtocol


@KeyDirective(fields="id")
class UserExtension(FederationType, schema_name="User"):
    id = FederationField(int)
    assigned_task_count = FederationField(int)

    @assigned_task_count.visible
    def assigned_task_count_visible(self: FederationField, request: DjangoRequestProtocol) -> bool:
        return request.user.is_staff
