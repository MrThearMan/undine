from undine import Entrypoint, Field, Input, MutationType, QueryType, RootType, create_schema

from .models import Project, Task


class ProjectType(QueryType[Project]):
    pk = Field()
    name = Field()


class TaskType(QueryType[Task]):
    pk = Field()
    name = Field()
    done = Field()
    created_at = Field()
    project = Field()


class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)


class TaskProjectInput(MutationType[Project], kind="related"):
    pk = Input()
    name = Input()


class TaskCreateMutation(MutationType[Task]):
    name = Input()
    done = Input()
    project = Input(TaskProjectInput)


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)


schema = create_schema(query=Query, mutation=Mutation)
