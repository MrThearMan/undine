from undine import Field, QueryType

from .models import Task


class TaskType(QueryType[Task], cache_time=10, cache_per_user=True):
    name = Field()
