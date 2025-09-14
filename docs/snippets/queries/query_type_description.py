from undine import Field, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    """Description."""

    name = Field()
