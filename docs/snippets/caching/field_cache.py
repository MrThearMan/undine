from undine import Entrypoint, Field, QueryType, RootType

from .models import Task


class TaskType(QueryType[Task], auto=False):
    name = Field(cache_time=10, cache_per_user=True)


class Query(RootType):
    task = Entrypoint(TaskType, cache_time=60)
