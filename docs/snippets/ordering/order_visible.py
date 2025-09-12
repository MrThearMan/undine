from undine import Order, OrderSet
from undine.typing import DjangoRequestProtocol

from .models import Task


class TaskOrderSet(OrderSet[Task]):
    name = Order()

    @name.visible
    def name_visible(self, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser
