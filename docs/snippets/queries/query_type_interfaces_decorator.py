from undine import Field, QueryType
from undine.relay import Node

from .models import Task


@Node
class TaskType(QueryType[Task]):
    name = Field()
