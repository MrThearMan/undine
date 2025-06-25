from undine import QueryType

from .models import Task


# This would create an empty `ObjectType`, which is not allowed in GraphQL.
class TaskType(QueryType[Task], auto=False): ...
