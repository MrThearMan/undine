from undine import Field, Order, OrderSet, QueryType

from .models import Task


class TaskOrderSet(OrderSet[Task]):
    name = Order()
    done = Order()
    created_at = Order()


@TaskOrderSet
class TaskType(QueryType[Task]):
    name = Field()
