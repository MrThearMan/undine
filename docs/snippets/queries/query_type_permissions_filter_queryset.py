from django.db.models import QuerySet

from undine import Field, GQLInfo, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    name = Field()

    @classmethod
    def __filter_queryset__(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
        if not info.context.user.is_authenticated:
            return queryset.none()
        return queryset
