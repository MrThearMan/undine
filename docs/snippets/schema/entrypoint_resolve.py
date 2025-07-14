from undine import Entrypoint, GQLInfo, QueryType, RootType
from undine.optimizer.optimizer import optimize_sync

from .models import Task


class TaskType(QueryType[Task]): ...


class Query(RootType):
    task_by_name = Entrypoint(TaskType, nullable=True)

    @task_by_name.resolve
    def resolve_task_by_name(self, info: GQLInfo, name: str) -> Task | None:
        return optimize_sync(Task.objects.all(), info, name=name)
