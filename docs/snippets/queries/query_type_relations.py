from undine import Field, QueryType

from .models import Project, Task


class ProjectType(QueryType[Project]):
    pk = Field()
    name = Field()
    tasks = Field()


class TaskType(QueryType[Task]):
    pk = Field()
    name = Field()
    done = Field()
    created_at = Field()
    project = Field()
