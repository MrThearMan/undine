from undine import Input, MutationType

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    name = Input(hidden=True, default_value="New task")
