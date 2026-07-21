from undine import GQLInfo
from undine.exceptions import GraphQLPermissionError
from undine.federation import FederationField, FederationType, KeyDirective


@KeyDirective(fields="id")
class UserExtension(FederationType, schema_name="User"):
    id = FederationField(int)
    assigned_task_count = FederationField(int)

    @assigned_task_count.resolve
    def resolve_assigned_task_count(self, info: GQLInfo) -> int:
        return 0

    @assigned_task_count.permissions
    def assigned_task_count_permissions(self, info: GQLInfo, value: int) -> None:
        if not info.context.user.is_staff:
            msg = "Only staff can see the assigned task count."
            raise GraphQLPermissionError(msg)
