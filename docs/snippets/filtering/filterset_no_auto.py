from undine import FilterSet

from .models import Task


# This would create an empty `InputObjectType`, which is not allowed in GraphQL.
class TaskFilterSet(FilterSet[Task], auto=False): ...
