from undine import Entrypoint, QueryType, RootType
from undine.pagination import OffsetPagination

from .models import Task


class TaskType(QueryType[Task]): ...


class Query(RootType):
    paged_tasks = Entrypoint(OffsetPagination(TaskType))
