from undine import Order, OrderSet

from .models import Task


class TaskOrderSet(OrderSet[Task]):
    title = Order(field_name="name")
