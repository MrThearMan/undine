from undine import QueryType

from .models import Task


class TaskType(QueryType[Task], auto=True, exclude=["name"]): ...
