from django.db.models import F, OuterRef, Q

from undine import DjangoExpression, Filter, FilterSet, GQLInfo
from undine.utils.model_utils import SubqueryCount

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    has_more_copies = Filter(Q(copies__gt=F("non_copies")))

    @has_more_copies.aliases
    def has_more_copies_aliases(self, info: GQLInfo, *, value: bool) -> dict[str, DjangoExpression]:
        return {
            "copies": SubqueryCount(Task.objects.filter(name=OuterRef("name"))),
            "non_copies": SubqueryCount(Task.objects.exclude(name=OuterRef("name"))),
        }
