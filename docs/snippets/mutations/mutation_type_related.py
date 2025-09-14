from undine import Input, MutationType

from .models import Project, Task


class TaskProject(MutationType[Project], kind="related"):
    pk = Input()
    name = Input()


class TaskCreateMutation(MutationType[Task]):
    name = Input()
    done = Input()
    project = Input(TaskProject)
