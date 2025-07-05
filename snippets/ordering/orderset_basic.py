from undine import OrderSet, QueryType

from .models import Task


class TaskOrderSet(OrderSet[Task]): ...


class TaskType(QueryType[Task], orderset=TaskOrderSet): ...
