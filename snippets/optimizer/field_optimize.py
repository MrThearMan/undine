from undine import Field, GQLInfo, QueryType
from undine.optimizer import OptimizationData

from .models import Project, Step, Task


class ProjectType(QueryType[Project]): ...


class TaskType(QueryType[Task]):
    name = Field()

    @name.optimize
    def optimize_name(self, data: OptimizationData, info: GQLInfo) -> None:
        data.only_fields.add("name")


class StepType(QueryType[Step]): ...
