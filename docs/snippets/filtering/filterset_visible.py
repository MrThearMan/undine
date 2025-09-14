from undine import Filter, FilterSet
from undine.typing import DjangoRequestProtocol

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    name = Filter()

    @classmethod
    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser
