from undine import Field, QueryType

from .models import Task


class TaskType(QueryType[Task], cache_for_seconds=10, cache_per_user=True):
    name = Field()
