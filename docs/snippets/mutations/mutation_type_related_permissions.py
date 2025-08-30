from typing import Any

from undine import GQLInfo, Input, MutationType

from .models import Project, Task


class TaskProject(MutationType[Project], kind="related"):
    @classmethod
    def __permissions__(cls, instance: Project, info: GQLInfo, input_data: dict[str, Any]) -> None:
        # Some permission check logic here
        return


class TaskCreateMutation(MutationType[Task]):
    project = Input(TaskProject)
