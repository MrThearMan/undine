from undine import Input, MutationType

from .models import Project, Task


class TaskCreateMutation(MutationType[Task]):
    project = Input(Project)
