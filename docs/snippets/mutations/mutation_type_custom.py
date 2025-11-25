from typing import Any

from undine import GQLInfo, Input, MutationType

from .models import Task


class TaskMutation(MutationType[Task], kind="create"):
    name = Input()

    @classmethod
    def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> Task:
        # Some custom mutation logic here
        return instance

    @classmethod
    def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: list[dict[str, Any]]) -> list[Task]:
        # Some custom bulk mutation logic here
        return instances
