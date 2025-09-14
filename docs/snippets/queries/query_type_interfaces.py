from undine import Field, QueryType
from undine.relay import Node

from .models import Task


class TaskType(QueryType[Task], interfaces=[Node]):
    name = Field()
