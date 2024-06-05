from undine import OrderSet

from .models import Task


class TaskOrderSet(OrderSet[Task], exclude=["pk"]): ...
