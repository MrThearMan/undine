from django.db.models import Q

from undine import Filter, FilterSet, GQLInfo
from undine.exceptions import GraphQLPermissionError

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    @Filter
    def name(self, info: GQLInfo, *, value: str) -> Q:
        if not info.context.user.is_authenticated:
            msg = "Only authenticated users can filter by task names."
            raise GraphQLPermissionError(msg)

        return Q(name__icontains=value)
