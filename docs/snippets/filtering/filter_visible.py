from undine import Filter, FilterSet
from undine.typing import DjangoRequestProtocol

from .models import Task


class TaskFilterSet(FilterSet[Task]):
    name = Filter()

    @name.visible
    def name_visible(self, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser
