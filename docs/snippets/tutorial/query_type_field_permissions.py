from undine import Entrypoint, Field, GQLInfo, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError

from .models import Project, Step, Task


class ProjectType(QueryType[Project]): ...


class TaskType(QueryType[Task]):
    name = Field()

    @name.permissions
    def name_permissions(self, info: GQLInfo, value: str) -> None:
        if info.context.user.is_anonymous:
            msg = "Need to be logged in to access the name of the Task."
            raise GraphQLPermissionError(msg)


class StepType(QueryType[Step]): ...


class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)


schema = create_schema(query=Query)
