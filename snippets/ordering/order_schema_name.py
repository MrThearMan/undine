from undine import Order, OrderSet

from .models import Task


class TaskOrderSet(OrderSet[Task]):
    name = Order(schema_name="title")
