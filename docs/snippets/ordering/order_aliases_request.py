from django.db.models import Case, F, Value, When

from undine import GQLInfo, Order, OrderSet
from undine.typing import DjangoExpression

from .models import Task


class TaskOrderSet(OrderSet[Task]):
    mine_first = Order(F("is_mine"))

    @mine_first.aliases
    def is_mine(self, info: GQLInfo, *, descending: bool) -> dict[str, DjangoExpression]:
        user = info.context.user
        if not user.is_authenticated:
            return {"is_mine": Value(0)}

        return {"is_mine": Case(When(assignee=user, then=Value(1)), default=Value(0))}
