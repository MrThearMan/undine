from typing import Any

from undine import GQLInfo, Input, MutationType

from .models import Project, Task


class TaskCreateMutation(MutationType[Task]):
    project = Input(Project)

    @classmethod
    def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        assert isinstance(input_data["project"], int)

    @classmethod
    def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        assert isinstance(input_data["project"], Project)
