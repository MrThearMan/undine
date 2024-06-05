from typing import Any

from undine import GQLInfo, Input, MutationType

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    logging_enabled = Input(bool, input_only=True)

    @classmethod
    def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        if input_data.get("logging_enabled"):
            print("Logging enabled")
