from undine import Field, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    name = Field(cache_time=10, cache_per_user=True)
