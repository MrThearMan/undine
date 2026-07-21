from undine import Entrypoint, Field, QueryType, RootType
from undine.federation import create_federation_schema

from .models import Task


class TaskType(QueryType[Task]):
    id = Field()
    name = Field()


class Query(RootType):
    task = Entrypoint(TaskType)


schema = create_federation_schema(query=Query)
