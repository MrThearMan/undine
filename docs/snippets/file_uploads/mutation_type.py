from undine import Entrypoint, MutationType, QueryType, RootType

from .models import Task


class TaskType(QueryType[Task], auto=True): ...


class TaskCreateMutation(MutationType[Task], auto=True): ...


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)
