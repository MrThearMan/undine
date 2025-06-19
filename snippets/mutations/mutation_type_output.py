from undine import Entrypoint, MutationType, QueryType, RootType

from .models import Task


class TaskType(QueryType[Task]): ...


class TaskCreateMutation(MutationType[Task]): ...


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)
