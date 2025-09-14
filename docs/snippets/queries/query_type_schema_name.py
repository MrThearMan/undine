from undine import Field, QueryType

from .models import Task


class TaskType(QueryType[Task], schema_name="Task"):
    name = Field()
