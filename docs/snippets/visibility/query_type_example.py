from undine import Entrypoint, Field, QueryType, RootType
from undine.typing import DjangoRequestProtocol

from .models import Task


class TaskType(QueryType[Task]):
    name = Field()

    @classmethod
    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        return request.user.is_authenticated


class Query(RootType):
    tasks = Entrypoint(TaskType, many=True)

    @Entrypoint
    def hello(self) -> str:
        return "world"
