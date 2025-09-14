from typing import Any

from undine import GQLInfo, Input, MutationType
from undine.exceptions import GraphQLValidationError

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    name = Input()

    @classmethod
    def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        if len(input_data["name"]) < 3:
            msg = "Name must be at least 3 characters long."
            raise GraphQLValidationError(msg)
