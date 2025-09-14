from undine import Order, OrderSet
from undine.typing import DjangoRequestProtocol

from .models import Task


class TaskOrderSet(OrderSet[Task]):
    name = Order()

    @classmethod
    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser
