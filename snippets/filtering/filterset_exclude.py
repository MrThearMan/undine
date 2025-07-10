from undine import FilterSet

from .models import Task


class TaskFilterSet(FilterSet[Task], exclude=["created_at"]): ...
