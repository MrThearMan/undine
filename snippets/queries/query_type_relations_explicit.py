from undine import Field, QueryType

from .models import Project, Task


class ProjectType(QueryType[Project]):
    tasks = Field(lambda: TaskType, many=True)  # lazy evaluation


class TaskType(QueryType[Task]):
    project = Field(ProjectType)
