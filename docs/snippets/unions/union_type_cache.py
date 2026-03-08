from undine import QueryType, UnionType

from .models import Project, Task


class TaskType(QueryType[Task]): ...


class ProjectType(QueryType[Project]): ...


class SearchObjects(UnionType[TaskType, ProjectType], cache_time=10, cache_per_user=True): ...
