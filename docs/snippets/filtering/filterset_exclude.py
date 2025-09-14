from undine import FilterSet

from .models import Task


class TaskFilterSet(FilterSet[Task], auto=True, exclude=["created_at"]): ...
