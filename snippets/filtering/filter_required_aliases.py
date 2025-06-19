from django.db.models import F, OuterRef, Q

from undine import Filter, FilterSet
from undine.utils.model_utils import SubqueryCount

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    has_more_copies = Filter(
        Q(copies__gt=F("non_copies")),
        required_aliases={
            "copies": SubqueryCount(Task.objects.filter(name=OuterRef("name"))),
            "non_copies": SubqueryCount(Task.objects.exclude(name=OuterRef("name"))),
        },
    )
