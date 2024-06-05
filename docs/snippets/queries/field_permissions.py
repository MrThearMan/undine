from undine import Field, GQLInfo, QueryType
from undine.exceptions import GraphQLPermissionError

from .models import Task


class TaskType(QueryType[Task]):
    name = Field()

    @name.permissions
    def name_permissions(self, info: GQLInfo, value: str) -> None:
        if not info.context.user.is_authenticated:
            msg = "Only authenticated users can query task names."
            raise GraphQLPermissionError(msg)
