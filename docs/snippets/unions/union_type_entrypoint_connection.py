from undine import Entrypoint, QueryType, RootType, UnionType
from undine.relay import Connection

from .models import Project, Task


class TaskType(QueryType[Task]): ...


class ProjectType(QueryType[Project]): ...


class SearchObjects(UnionType[TaskType, ProjectType]): ...


class Query(RootType):
    search_objects = Entrypoint(Connection(SearchObjects))
