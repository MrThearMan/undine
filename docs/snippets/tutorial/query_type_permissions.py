from undine import GQLInfo, QueryType
from undine.exceptions import GraphQLPermissionError

from .models import Task


class TaskType(QueryType[Task]):
    @classmethod
    def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
        if info.context.user.is_anonymous:
            msg = "Need to be logged in to access Tasks."
            raise GraphQLPermissionError(msg)
