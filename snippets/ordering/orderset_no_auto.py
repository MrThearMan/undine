from undine import OrderSet

from .models import Task


# This would create an empty `Enum`, which is not allowed in GraphQL.
class TaskOrderSet(OrderSet[Task], auto=False): ...
