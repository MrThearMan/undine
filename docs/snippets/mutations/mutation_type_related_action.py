from undine import Input, MutationType

from .models import Project, Task


class ProjectTask(MutationType[Task], kind="related", related_action="delete"): ...


# Update given project and its tasks, deleting any tasks that are not given in the mutation.
class ProjectUpdateMutation(MutationType[Project]):
    tasks = Input(ProjectTask)
