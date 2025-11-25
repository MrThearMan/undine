from undine import QueryType, UnionType
from undine.typing import DjangoRequestProtocol

from .models import Project, Task


class TaskType(QueryType[Task]): ...


class ProjectType(QueryType[Project]): ...


class SearchObjects(UnionType[TaskType, ProjectType]):
    @classmethod
    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser
