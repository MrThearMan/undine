from undine import Field, GQLInfo, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    name = Field(nullable=True)

    @name.resolve
    def name_resolver(self, info: GQLInfo) -> str | None:
        if not info.context.user.is_authenticated:
            return None
        return self.name
