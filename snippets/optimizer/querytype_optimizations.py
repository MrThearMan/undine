from undine import GQLInfo, QueryType
from undine.optimizer import OptimizationData

from .models import Project, Step, Task


class ProjectType(QueryType[Project]): ...


class TaskType(QueryType[Task]):
    @classmethod
    def __optimizations__(cls, data: OptimizationData, info: GQLInfo) -> None:
        data.only_fields.add("name")
        data.add_select_related("project", query_type=ProjectType)
        data.add_prefetch_related("steps", query_type=StepType)


class StepType(QueryType[Step]): ...
