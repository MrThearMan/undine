from undine import MutationType

from .models import Task


class TaskCreateMutation(MutationType[Task], kind="create"): ...
