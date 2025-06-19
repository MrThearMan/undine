from undine import QueryType

from .models import Task


class TaskType(QueryType[Task], exclude=["name"]): ...
