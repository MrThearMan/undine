from undine import Entrypoint, GQLInfo, QueryType, RootType
from undine.exceptions import GraphQLPermissionError

from .models import Task


class TaskType(QueryType[Task]):
    @classmethod
    def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
        # Not called if 'TaskType' is accessed from 'Query.task'
        # because it has a permissions check already
        if not info.context.user.is_superuser:
            raise GraphQLPermissionError


class Query(RootType):
    task = Entrypoint(TaskType)

    @task.permissions
    def task_permissions(self, info: GQLInfo, instance: Task) -> None:
        if info.context.user.is_authenticated:
            msg = "Need to be logged in to access Tasks."
            raise GraphQLPermissionError(msg)
