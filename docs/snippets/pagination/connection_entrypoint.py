from undine import Entrypoint, QueryType, RootType
from undine.relay import Connection

from .models import Task


class TaskType(QueryType[Task]): ...


class Query(RootType):
    paged_tasks = Entrypoint(Connection(TaskType))
