from undine import Filter, FilterSet

from .models import Task


class TaskFilterSet(FilterSet[Task], extensions={"foo": "bar"}):
    name = Filter()
