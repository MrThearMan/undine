from undine import Entrypoint, QueryType, RootType
from undine.relay import Connection, PaginationHandler

from .models import Task


class CustomPaginationHandler(PaginationHandler):
    """Custom pagination logic."""


class TaskType(QueryType[Task]): ...


class Query(RootType):
    paged_tasks = Entrypoint(Connection(TaskType, pagination_handler=CustomPaginationHandler))
