"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings
"""

from typing import TypedDict

from example_project.app.models import Task
from undine import GQLInfo, MutationType


class TaskCreateMutationFullInputData(TypedDict):
    name: str
    check: bool


class TaskCreateMutationInputData(TypedDict):
    name: str


class TaskCreateMutation(MutationType[Task]):
    @classmethod
    def __permissions__(cls, instance: Task, info: GQLInfo, input_data: TaskCreateMutationFullInputData) -> None: ...

    @classmethod
    def __validate__(cls, instance: Task, info: GQLInfo, input_data: TaskCreateMutationFullInputData) -> None: ...

    @classmethod
    def __mutate__(cls, instance: Task, info: GQLInfo, input_data: TaskCreateMutationInputData) -> None: ...

    @classmethod
    def __bulk_mutate__(
        cls,
        instances: list[Task],
        info: GQLInfo,
        input_data: list[TaskCreateMutationInputData],
    ) -> None: ...

    @classmethod
    def __after__(cls, instance: Task, info: GQLInfo, input_data: TaskCreateMutationInputData) -> None: ...
