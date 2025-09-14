from undine import Filter, FilterSet

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    """Description."""

    name = Filter()
