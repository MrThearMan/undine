from undine import Field, GQLInfo, QueryType
from undine.exceptions import GraphQLPermissionError

from .models import Task


class TaskType(QueryType[Task]):
    name = Field()

    @name.permissions
    def name_permissions(self, info: GQLInfo, value: str) -> None:
        if info.context.user.is_anonymous:
            msg = "Need to be logged in to access the name of the Task."
            raise GraphQLPermissionError(msg)
