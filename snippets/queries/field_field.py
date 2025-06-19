from undine import Field, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    name = Field(Task.name)
