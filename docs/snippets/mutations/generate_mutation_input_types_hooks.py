from __future__ import annotations

from typing import TYPE_CHECKING

from undine import Input, MutationType

from .models import Task

if TYPE_CHECKING:
    from undine import GQLInfo

    from .gql_input_types import TaskCreateMutationFullInputData, TaskCreateMutationInputData


class TaskCreateMutation(MutationType[Task]):
    name = Input()

    @classmethod
    def __permissions__(
        cls,
        instance: Task,
        info: GQLInfo,
        input_data: TaskCreateMutationFullInputData,
    ) -> None: ...

    @classmethod
    def __validate__(
        cls,
        instance: Task,
        info: GQLInfo,
        input_data: TaskCreateMutationFullInputData,
    ) -> None: ...

    @classmethod
    def __mutate__(
        cls,
        instance: Task,
        info: GQLInfo,
        input_data: TaskCreateMutationInputData,
    ) -> None: ...

    @classmethod
    def __bulk_mutate__(
        cls,
        instances: list[Task],
        info: GQLInfo,
        input_data: list[TaskCreateMutationInputData],
    ) -> None: ...

    @classmethod
    def __after__(
        cls,
        instance: Task,
        info: GQLInfo,
        input_data: TaskCreateMutationInputData,
    ) -> None: ...
