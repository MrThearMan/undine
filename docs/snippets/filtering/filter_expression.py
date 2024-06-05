from django.db.models.functions import Upper

from undine import Filter, FilterSet

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    name_upper = Filter(Upper("name"))
