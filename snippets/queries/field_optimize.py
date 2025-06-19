from undine import Field, GQLInfo, QueryType
from undine.optimizer import OptimizationData

from .models import Task


class TaskType(QueryType[Task]):
    name = Field()

    @name.optimize
    def optimize_name(self, data: OptimizationData, info: GQLInfo) -> None:
        pass  # Some optimization here
