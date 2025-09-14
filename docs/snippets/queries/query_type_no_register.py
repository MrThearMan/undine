from undine import Field, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    name = Field()


class OtherTaskType(QueryType[Task], register=False):
    pk = Field()
