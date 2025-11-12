from undine import Entrypoint, Field, QueryType, RootType
from undine.pagination import OffsetPagination

from .models import Person, Task


class PersonType(QueryType[Person]): ...


class TaskType(QueryType[Task]):
    assignees = Field(OffsetPagination(PersonType))


class Query(RootType):
    paged_tasks = Entrypoint(OffsetPagination(TaskType))
