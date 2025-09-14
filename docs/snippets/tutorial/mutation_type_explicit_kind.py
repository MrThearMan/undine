from undine import Input, MutationType

from .models import Task


class TaskCreateMutation(MutationType[Task], kind="create"):
    name = Input()
    done = Input()
