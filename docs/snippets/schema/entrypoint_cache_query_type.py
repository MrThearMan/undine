from undine import Entrypoint, Field, QueryType, RootType

from .models import Project, Task


class ProjectType(QueryType[Project], auto=False, cache_for_seconds=10):
    name = Field()


class TaskType(QueryType[Task], auto=False):
    project = Field(ProjectType)


class Query(RootType):
    task = Entrypoint(TaskType, cache_for_seconds=60)
