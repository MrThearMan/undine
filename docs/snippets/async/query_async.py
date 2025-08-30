from undine import Field, GQLInfo, QueryType

from .models import Task


class TaskType(QueryType[Task]):
    name = Field()

    @name.resolve
    async def resolve_name(self, info: GQLInfo) -> str:
        return self.name

    @name.permissions
    async def permissions(self, info: GQLInfo, value: str) -> None:
        return
