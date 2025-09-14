from undine import Field, GQLInfo, QueryType
from undine.optimizer import OptimizationData

from .models import Task


class TaskType(QueryType[Task]):
    name = Field()

    @classmethod
    def __optimizations__(cls, data: OptimizationData, info: GQLInfo) -> None:
        pass  # Some optimization here
