from typing import Any

from asgiref.sync import sync_to_async

from example_project.app.models import Task
from undine import GQLInfo, MutationType


class CustomTaskMutation(MutationType[Task]):
    @classmethod
    async def __mutate__(cls, root: Task, info: GQLInfo, input_data: dict[str, Any]) -> Any:
        await sync_to_async(Task.objects.create)(name=input_data["name"])
