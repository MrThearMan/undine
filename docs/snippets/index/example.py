import asyncio
from collections.abc import AsyncIterator
from typing import Any

from undine import (
    Entrypoint,
    Field,
    Filter,
    FilterSet,
    GQLInfo,
    Input,
    MutationType,
    Order,
    OrderSet,
    QueryType,
    RootType,
    create_schema,
)
from undine.exceptions import GraphQLPermissionError, GraphQLValidationError
from undine.relay import Connection, Node
from undine.subscriptions import ModelCreateSubscription

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    name = Filter(lookup="icontains")
    done = Filter()


class TaskOrderSet(OrderSet[Task]):
    id = Order()
    name = Order(null_placement="last")


@Node
@TaskFilterSet
@TaskOrderSet
class TaskType(QueryType[Task], schema_name="Task"):
    pk = Field()
    name = Field()

    @name.permissions
    def name_permissions(self, instance: Task, info: GQLInfo) -> None:
        if not info.context.user.is_authenticated:
            raise GraphQLPermissionError


class TaskCreateMutation(MutationType[Task]):
    name = Input()
    done = Input(default_value=False)

    @classmethod
    def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        if not info.context.user.is_staff:
            msg = "Only staff members can create tasks"
            raise GraphQLPermissionError(msg)

    @classmethod
    def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        if len(input_data["name"]) < 3:
            msg = "Task name must be at least 3 characters"
            raise GraphQLValidationError(msg)


class Query(RootType):
    node = Entrypoint(Node)
    task = Entrypoint(TaskType, cache_time=10)
    tasks = Entrypoint(Connection(TaskType))


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)
    bulk_create_tasks = Entrypoint(TaskCreateMutation, many=True)


class Subscription(RootType):
    task_created = Entrypoint(ModelCreateSubscription(TaskType))

    @Entrypoint
    async def countdown(self, info: GQLInfo) -> AsyncIterator[int]:
        for i in range(10, -1, -1):
            yield i
            await asyncio.sleep(1)


schema = create_schema(query=Query, mutation=Mutation, subscription=Subscription)
