from undine import Entrypoint, QueryType, RootType

from .models import Task


class TaskType(QueryType[Task]): ...


class Query(RootType):
    tasks = Entrypoint(TaskType, many=True, limit=100)
