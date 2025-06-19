from undine import MutationType

from .models import Task


# This would create an empty `InputObjectType`, which is not allowed in GraphQL.
class TaskCreateMutation(MutationType[Task], auto=False): ...
