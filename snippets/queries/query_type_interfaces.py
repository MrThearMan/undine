from undine import QueryType
from undine.relay import Node

from .models import Task


class TaskType(QueryType[Task], interfaces=[Node]): ...
