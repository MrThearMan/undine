from undine import Order, OrderSet

from .models import Task


class TaskOrderSet(OrderSet[Task]):
    name = Order(null_placement="first")
    created_at = Order(null_placement="last")
