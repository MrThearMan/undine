from django.db.models.functions import Lower

from undine import DjangoExpression, GQLInfo, Order, OrderSet

from .models import Task


class TaskOrderSet(OrderSet[Task]):
    name = Order("name_lower")

    @name.aliases
    def name_lower(self, info: GQLInfo, *, descending: bool) -> dict[str, DjangoExpression]:
        return {"name_lower": Lower("name")}
