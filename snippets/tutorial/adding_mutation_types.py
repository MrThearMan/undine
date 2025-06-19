from undine import Entrypoint, MutationType, QueryType, RootType, create_schema

from .models import Project, Step, Task


class ProjectType(QueryType[Project]): ...


class TaskType(QueryType[Task]): ...


class StepType(QueryType[Step]): ...


class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)


class TaskCreateMutation(MutationType[Task]): ...


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)


schema = create_schema(query=Query, mutation=Mutation)
