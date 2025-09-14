from typing import Any

from undine import GQLInfo, Input, MutationType

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    name = Input()

    @classmethod
    def __after__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        pass  # Some post-mutation handling here
