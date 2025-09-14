from undine import Field, Filter, FilterSet, QueryType

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    name = Filter()


class TaskType(QueryType[Task], filterset=TaskFilterSet):
    name = Field()
