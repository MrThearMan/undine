from undine import Field, QueryType

from .models import Project, Task


class ProjectType(QueryType[Project]): ...


class TaskType(QueryType[Task]):
    project = Field(ProjectType, field_name="task_list")
