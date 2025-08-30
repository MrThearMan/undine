from typing import Any

from undine import GQLInfo, Input, MutationType

from .models import Task


class CustomTaskMutation(MutationType[Task]):
    name = Input()

    @name.validate
    async def validate(self, info: GQLInfo, value: str) -> None:
        return

    @name.permissions
    async def permissions(self, info: GQLInfo, value: str) -> None:
        return

    @classmethod
    async def __mutate__(cls, root: Task, info: GQLInfo, input_data: dict[str, Any]) -> Any:
        return

    @classmethod
    async def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: list[dict[str, Any]]) -> Any:
        return

    @classmethod
    async def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        return

    @classmethod
    async def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        return

    @classmethod
    async def __after__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        return
