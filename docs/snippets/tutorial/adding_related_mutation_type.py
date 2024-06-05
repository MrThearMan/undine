from undine import Entrypoint, Input, MutationType, QueryType, RootType, create_schema

from .models import Project, Step, Task


class ProjectType(QueryType[Project]): ...


class TaskType(QueryType[Task]): ...


class StepType(QueryType[Step]): ...


class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)


class TaskProjectInput(MutationType[Project], kind="related"): ...


class TaskCreateMutation(MutationType[Task]):
    project = Input(TaskProjectInput)


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)


schema = create_schema(query=Query, mutation=Mutation)
