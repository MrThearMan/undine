from undine import Input, MutationType

from .models import Task


class TaskCreateMutation(MutationType[Task]):
    title = Input("name")
