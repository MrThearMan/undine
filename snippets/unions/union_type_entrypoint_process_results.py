from undine import GQLInfo, QueryType, UnionType

from .models import Project, Task


class TaskType(QueryType[Task]): ...


class ProjectType(QueryType[Project]): ...


class SearchObjects(UnionType[TaskType, ProjectType]):
    @classmethod
    def __process_results__(cls, instances: list[Task | Project], info: GQLInfo) -> list[Task | Project]:
        return sorted(instances, key=lambda i: i.name)
