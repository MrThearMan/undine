from undine import MutationType, QueryType

from .models import Task


class TaskType(QueryType[Task]): ...


class TaskCreateMutation(MutationType[Task]):
    @classmethod
    def __query_type__(cls) -> type[QueryType]:
        return TaskType
