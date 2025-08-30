from undine import Input, MutationType

from .models import Project, Task


class TaskProject(MutationType[Project], kind="related"): ...


class TaskCreateMutation(MutationType[Task]):
    project = Input(TaskProject)
