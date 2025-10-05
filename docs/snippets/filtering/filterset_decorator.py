from undine import Field, Filter, FilterSet, QueryType

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    name = Filter()


@TaskFilterSet
class TaskType(QueryType[Task]):
    name = Field()
