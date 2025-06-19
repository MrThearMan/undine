from django.db.models import QuerySet

from undine import FilterSet, GQLInfo

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    @classmethod
    def __filter_queryset__(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
        if not info.context.user.is_staff:
            return queryset.none()
        return queryset
