from undine import GQLInfo, QueryType
from undine.optimizer import OptimizationData

from .models import Task


class TaskType(QueryType[Task]):
    @classmethod
    def __optimizations__(cls, data: OptimizationData, info: GQLInfo) -> None:
        pass  # Some optimization here
