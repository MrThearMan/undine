from undine import Filter, FilterSet

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    # Allow filtering with the empty string or None
    title = Filter(empty_values=[])
