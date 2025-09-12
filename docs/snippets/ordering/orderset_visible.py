from undine import OrderSet
from undine.typing import DjangoRequestProtocol

from .models import Task


class TaskOrderSet(OrderSet[Task]):
    @classmethod
    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser
