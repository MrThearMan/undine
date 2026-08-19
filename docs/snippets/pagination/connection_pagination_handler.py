from undine import Entrypoint, QueryType, RootType
from undine.relay import Connection, CursorPaginationHandler

from .models import Task


class CustomPaginationHandler(CursorPaginationHandler):
    """Custom pagination logic."""


class TaskType(QueryType[Task]): ...


class Query(RootType):
    paged_tasks = Entrypoint(Connection(TaskType, pagination_handler=CustomPaginationHandler))
