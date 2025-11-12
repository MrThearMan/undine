from undine import Entrypoint, Field, Input, MutationType, QueryType, RootType

from .models import Task


# This QueryType is registered and then used
# by TaskCreateMutation as its output type since
# they have the same Django Model.
class TaskType(QueryType[Task]):
    pk = Field()
    name = Field()
    done = Field()
    created_at = Field()


class TaskCreateMutation(MutationType[Task]):
    name = Input()


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)
