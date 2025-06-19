from undine import Field, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    name = Field(schema_name="title")
