from undine import GQLInfo, Input, MutationType
from undine.exceptions import GraphQLPermissionError

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    done = Input()

    @done.permissions
    def done_permissions(self, info: GQLInfo, value: bool) -> None:
        if not info.context.user.is_superuser:
            msg = "Must be a superuser to be able add done tasks."
            raise GraphQLPermissionError(msg)
