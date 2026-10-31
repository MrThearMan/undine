from undine import Entrypoint, QueryType, RootType
from undine.relay import Connection, Node

from .models import Task


class TaskType(QueryType[Task], interfaces=[Node]): ...


class Query(RootType):
    node = Entrypoint(Node)
    tasks = Entrypoint(Connection(TaskType))
