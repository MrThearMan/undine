from undine import GQLInfo
from undine.exceptions import GraphQLPermissionError
from undine.federation import FederationField, FederationType, KeyDirective


@KeyDirective(fields="id")
class UserExtension(FederationType, schema_name="User"):
    id = FederationField(int)
    assigned_task_count = FederationField(int)

    @classmethod
    def __permissions__(cls, instance: "UserExtension", info: GQLInfo) -> None:
        if not info.context.user.is_authenticated:
            msg = "Only authenticated users can resolve User extensions."
            raise GraphQLPermissionError(msg)

    @assigned_task_count.resolve
    def resolve_assigned_task_count(self, info: GQLInfo) -> int:
        return 0
