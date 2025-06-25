from undine import Entrypoint, Field, GQLInfo, QueryType, RootType

from .models import Task


class TaskType(QueryType[Task]):
    name = Field()

    @name.resolve
    async def resolve_name(self, info: GQLInfo) -> str:
        return self.name


class Query(RootType):
    tasks = Entrypoint(TaskType, many=True)

    @Entrypoint
    async def example(self, info: GQLInfo) -> str:
        return "foo"
