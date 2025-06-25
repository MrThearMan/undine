from undine import Filter, FilterSet

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    name = Filter(description="Get only tasks with the given name.")
