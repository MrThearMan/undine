from undine import Input, MutationType

from .models import Project, Task


class ProjectTask(MutationType[Task], kind="related"): ...


class ProjectUpdateMutation(MutationType[Project], related_action="delete"):
    tasks = Input(ProjectTask)
