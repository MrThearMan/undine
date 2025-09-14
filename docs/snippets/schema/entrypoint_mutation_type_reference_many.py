from undine import Entrypoint, Field, Input, MutationType, QueryType, RootType

from .models import Task


class TaskType(QueryType[Task]):
    pk = Field()
    name = Field()
    done = Field()
    created_at = Field()


class TaskCreateMutation(MutationType[Task]):
    name = Input()
    done = Input()


class Mutation(RootType):
    bulk_create_tasks = Entrypoint(TaskCreateMutation, many=True)
