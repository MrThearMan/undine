from undine import Field, Filter, FilterSet, QueryType

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    name_contains = Filter(lookup="icontains")
    done = Filter()


class TaskType(QueryType[Task], filterset=TaskFilterSet):
    pk = Field()
    name = Field()
    done = Field()
    created_at = Field()
