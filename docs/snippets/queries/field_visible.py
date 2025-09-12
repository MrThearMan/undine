from undine import Field, QueryType
from undine.typing import DjangoRequestProtocol

from .models import Task


class TaskType(QueryType[Task]):
    name = Field()

    @name.visible
    def name_visible(self, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser
