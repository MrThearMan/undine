from typing import Any

from undine import GQLInfo, MutationType

from .models import Task


class TaskMutation(MutationType[Task], kind="custom"):
    @classmethod
    def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Task:
        # Some custom mutation logic here
        return instance
