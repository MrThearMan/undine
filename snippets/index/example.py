from typing import Any

from undine import Entrypoint, FilterSet, GQLInfo, MutationType, OrderSet, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError
from undine.relay import Connection

from .models import Task


class TaskFilterSet(FilterSet[Task]): ...


class TaskOrderSet(OrderSet[Task]): ...


class TaskType(QueryType[Task], filterset=TaskFilterSet, orderset=TaskOrderSet): ...


class TaskCreateMutation(MutationType[Task]):
    @classmethod
    def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        if not info.context.user.is_staff:
            raise GraphQLPermissionError


class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(Connection(TaskType))


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)
    bulk_create_tasks = Entrypoint(TaskCreateMutation, many=True)


schema = create_schema(query=Query, mutation=Mutation)
