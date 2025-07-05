from undine import GQLInfo, Input, MutationType
from undine.exceptions import GraphQLPermissionError

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    name = Input()

    @name.permissions
    def name_permissions(self, info: GQLInfo, value: str) -> None:
        if not info.context.user.is_authenticated:
            msg = "Only authenticated users can set task names."
            raise GraphQLPermissionError(msg)
