from typing import Any

from undine import GQLInfo, MutationType

from .models import Task


class TaskMutation(MutationType[Task]):
    @classmethod
    def __mutate__(cls, root: Any, info: GQLInfo, input_data: dict[str, Any]) -> Any:
        pass  # Some custom mutation logic here
