from undine import Entrypoint, Input, MutationType, QueryType, RootType, create_schema

from .models import Project, Step, Task


class ProjectType(QueryType[Project]): ...


class TaskType(QueryType[Task]): ...


class StepType(QueryType[Step]): ...


class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)


class RelatedProject(MutationType[Project], kind="related"): ...


class TaskCreateMutation(MutationType[Task]):
    project = Input(RelatedProject)


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)
    bulk_create_tasks = Entrypoint(TaskCreateMutation, many=True)


schema = create_schema(query=Query, mutation=Mutation)
