from undine import Input, MutationType

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    name = Input()
    """The name of the task."""
