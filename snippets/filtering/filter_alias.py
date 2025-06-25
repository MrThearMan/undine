from undine import Filter, FilterSet

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    title = Filter("name")
