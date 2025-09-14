from undine import Filter, FilterSet

from .models import Task


class TaskFilterSet(FilterSet[Task], schema_name="TaskFilterInput"):
    name = Filter()
