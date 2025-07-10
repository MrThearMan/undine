from undine import FilterSet, QueryType

from .models import Task


class TaskFilterSet(FilterSet[Task]): ...


class TaskType(QueryType[Task], filterset=TaskFilterSet): ...
