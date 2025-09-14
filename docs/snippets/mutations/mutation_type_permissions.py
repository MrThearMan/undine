from typing import Any

from undine import GQLInfo, Input, MutationType
from undine.exceptions import GraphQLPermissionError

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    name = Input()

    @classmethod
    def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        if not info.context.user.is_authenticated:
            msg = "Only authenticated users can create tasks."
            raise GraphQLPermissionError(msg)
