from undine import Field, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    name = Field(deprecation_reason="Use something else.")
