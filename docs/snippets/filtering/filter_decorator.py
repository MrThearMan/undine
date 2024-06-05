from django.db.models import Q

from undine import Filter, FilterSet, GQLInfo

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    @Filter
    def name(self, info: GQLInfo, *, value: str) -> Q:
        return Q(name__iexact=value)
