from undine import Entrypoint, Field, QueryType, RootType

from .models import Task


class TaskType(QueryType[Task]):
    pk = Field()
    name = Field()
    done = Field()
    created_at = Field()


class Query(RootType):
    task = Entrypoint(TaskType)
