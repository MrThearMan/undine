from typing import Any

from undine import GQLInfo, MutationType
from undine.exceptions import GraphQLValidationError

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    @classmethod
    def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        if input_data["done"]:
            msg = "Cannot create a done task."
            raise GraphQLValidationError(msg)
