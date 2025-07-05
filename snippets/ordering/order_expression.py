from django.db.models.functions import Reverse

from undine import Order, OrderSet

from .models import Task


class TaskOrderSet(OrderSet[Task]):
    name = Order(Reverse("name"))
