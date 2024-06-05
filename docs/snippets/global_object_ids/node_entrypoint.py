from undine import Entrypoint, QueryType
from undine.relay import Connection, Node

from .models import Task


class TaskType(QueryType[Task], interfaces=[Node]): ...


class Query(QueryType):
    node = Entrypoint(Node)
    tasks = Entrypoint(Connection(TaskType))
