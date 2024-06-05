from undine import Filter, FilterSet, GQLInfo
from undine.exceptions import EmptyFilterResult

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    @Filter
    def name(self, info: GQLInfo, *, value: str) -> bool:
        if value == "secret":
            raise EmptyFilterResult
        return True
