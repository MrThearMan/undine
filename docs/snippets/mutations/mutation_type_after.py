from typing import Any

from undine import GQLInfo, MutationType

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    @classmethod
    def __after__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        pass  # Some post-mutation handling here
