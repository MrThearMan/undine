from undine import MutationType

from .models import Task


# Create mutation, since has "create" in the name.
class TaskCreateMutation(MutationType[Task]): ...
