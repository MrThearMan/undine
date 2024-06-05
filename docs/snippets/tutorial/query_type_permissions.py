from undine import Entrypoint, GQLInfo, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError

from .models import Project, Step, Task


class ProjectType(QueryType[Project]): ...


class TaskType(QueryType[Task]):
    @classmethod
    def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
        if info.context.user.is_anonymous:
            msg = "Need to be logged in to access Tasks."
            raise GraphQLPermissionError(msg)


class StepType(QueryType[Step]): ...


class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)


# Mutations removed for brevity

schema = create_schema(query=Query)
