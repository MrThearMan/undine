from undine import Field, Order, OrderSet, QueryType

from .models import Task


class TaskOrderSet(OrderSet[Task]):
    pk = Order()
    name = Order()


class TaskType(QueryType[Task], orderset=TaskOrderSet):
    pk = Field()
    name = Field()
    done = Field()
    created_at = Field()
