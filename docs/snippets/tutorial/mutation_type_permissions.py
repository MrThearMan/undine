from typing import Any

from undine import GQLInfo, MutationType
from undine.exceptions import GraphQLPermissionError

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    @classmethod
    def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        if not info.context.user.is_staff:
            msg = "Must be a staff user to be able add tasks."
            raise GraphQLPermissionError(msg)
