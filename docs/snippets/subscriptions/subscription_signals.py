from undine import Entrypoint, QueryType, RootType, create_schema
from undine.subscriptions import ModelCreateSubscription

from .models import Task


class TaskType(QueryType[Task], auto=True): ...


class Query(RootType):
    tasks = Entrypoint(TaskType, many=True)


class Subscription(RootType):
    created_tasks = Entrypoint(ModelCreateSubscription(TaskType))


schema = create_schema(query=Query, subscription=Subscription)
