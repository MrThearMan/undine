from undine import Entrypoint, Field, Input, MutationType, QueryType, RootType, create_schema

from .models import Task


class TaskType(QueryType[Task]):
    pk = Field()
    name = Field()
    done = Field()
    created_at = Field()


class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)


class TaskCreateMutation(MutationType[Task]):
    name = Input()
    done = Input()


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)


schema = create_schema(query=Query, mutation=Mutation)
