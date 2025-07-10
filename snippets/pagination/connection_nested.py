from undine import Entrypoint, Field, QueryType, RootType
from undine.relay import Connection

from .models import Person, Task


class PersonType(QueryType[Person]): ...


class TaskType(QueryType[Task]):
    assignees = Field(Connection(PersonType))


class Query(RootType):
    paged_tasks = Entrypoint(Connection(TaskType))
