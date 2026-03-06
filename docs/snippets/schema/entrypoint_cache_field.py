from undine import Entrypoint, Field, QueryType, RootType

from .models import Task


class TaskType(QueryType[Task], auto=False):
    name = Field(cache_for_seconds=10, cache_per_user=True)


class Query(RootType):
    task = Entrypoint(TaskType, cache_for_seconds=60)
