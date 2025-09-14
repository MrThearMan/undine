from undine import Input, MutationType

from .models import Task


class TaskCreateMutation(MutationType[Task], schema_name="CreateTask"):
    name = Input()
