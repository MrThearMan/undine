from undine import Input, MutationType

from .models import Task


class TaskMutation(MutationType[Task]):
    name = Input()
    done = Input()
