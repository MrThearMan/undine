from undine import Field, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    title = Field(field_name="name")
