from undine import QueryType
from undine.typing import DjangoRequestProtocol

from .models import Task


class TaskType(QueryType[Task]):
    @classmethod
    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser
