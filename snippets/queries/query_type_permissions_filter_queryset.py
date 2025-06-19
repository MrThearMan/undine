from django.db.models import QuerySet

from undine import GQLInfo, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    @classmethod
    def __filter_queryset__(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
        if not info.context.user.is_authenticated:
            return queryset.none()
        return queryset
