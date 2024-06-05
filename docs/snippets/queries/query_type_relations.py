from undine import QueryType

from .models import Project, Task


class ProjectType(QueryType[Project]): ...


class TaskType(QueryType[Task]): ...
