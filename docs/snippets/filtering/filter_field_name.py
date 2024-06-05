from undine import Filter, FilterSet

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    field_name = Filter(field_name="name")
