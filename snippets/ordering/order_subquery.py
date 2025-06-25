from django.db.models import OuterRef

from undine import Order, OrderSet
from undine.utils.model_utils import SubqueryCount

from .models import Task


class TaskOrderSet(OrderSet[Task]):
    copies = Order(SubqueryCount(Task.objects.filter(name=OuterRef("name"))))
