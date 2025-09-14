from undine import Field, QueryType

from .models import Task


class TaskType(QueryType[Task], extensions={"foo": "bar"}):
    name = Field()
