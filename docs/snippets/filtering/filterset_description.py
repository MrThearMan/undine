from undine import FilterSet

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    """Description."""
