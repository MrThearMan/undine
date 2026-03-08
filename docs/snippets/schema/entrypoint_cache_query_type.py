from undine import Entrypoint, Field, QueryType, RootType

from .models import Project, Task


class ProjectType(QueryType[Project], auto=False, cache_time=10):
    name = Field()


class TaskType(QueryType[Task], auto=False):
    project = Field(ProjectType)


class Query(RootType):
    task = Entrypoint(TaskType, cache_time=60)
