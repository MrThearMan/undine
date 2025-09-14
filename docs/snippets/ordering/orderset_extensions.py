from undine import Order, OrderSet

from .models import Task


class TaskOrderSet(OrderSet[Task], extensions={"foo": "bar"}):
    name = Order()
