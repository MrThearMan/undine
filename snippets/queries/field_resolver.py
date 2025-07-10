from undine import Field, GQLInfo, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    name = Field()

    @name.resolve
    def resolve_name(self, info: GQLInfo) -> str:
        return self.name.upper()
