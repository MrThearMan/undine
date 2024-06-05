from undine import Entrypoint, QueryType, RootType

from .models import Task


class TaskType(QueryType[Task]): ...


class Query(RootType):
    task = Entrypoint(TaskType, schema_name="singleTask")
