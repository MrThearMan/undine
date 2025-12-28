from undine import Entrypoint, MutationType, QueryType, RootType

from .models import Project, Task


class TaskType(QueryType[Task], auto=True): ...


class TaskCreateMutation(MutationType[Task], auto=True): ...


class ProjectType(QueryType[Project], auto=True): ...


class ProjectCreateMutation(MutationType[Project], auto=True): ...


class Query(RootType):
    tasks = Entrypoint(TaskType)
    projects = Entrypoint(ProjectType)


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)
    create_project = Entrypoint(ProjectCreateMutation)
