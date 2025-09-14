from undine import Input, MutationType

from .models import Task


class TaskMutation(MutationType[Task], kind="create"):
    name = Input()
