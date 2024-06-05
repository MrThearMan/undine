from django.db.models import OuterRef

from undine import Filter, FilterSet
from undine.utils.model_utils import SubqueryCount

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    copies = Filter(SubqueryCount(Task.objects.filter(name=OuterRef("name"))))
