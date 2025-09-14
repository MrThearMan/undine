from undine import Input, MutationType

from .models import Project, Task


class ProjectTask(MutationType[Task], kind="related"):
    pk = Input()
    name = Input()


class ProjectUpdateMutation(MutationType[Project], related_action="delete"):
    pk = Input()
    name = Input()
    done = Input()
    tasks = Input(ProjectTask)
