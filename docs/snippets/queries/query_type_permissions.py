from undine import Field, GQLInfo, QueryType
from undine.exceptions import GraphQLPermissionError

from .models import Task


class TaskType(QueryType[Task]):
    name = Field()

    @classmethod
    def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
        if not info.context.user.is_authenticated:
            msg = "Only authenticated users can query tasks."
            raise GraphQLPermissionError(msg)
