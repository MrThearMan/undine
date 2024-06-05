from typing import Any

from undine import Entrypoint, GQLInfo, MutationType, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError

from .models import Project, Step, Task


class ProjectType(QueryType[Project]): ...


class TaskType(QueryType[Task]): ...


class StepType(QueryType[Step]): ...


class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)


class TaskCreateMutation(MutationType[Task]):
    @classmethod
    def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
        if not info.context.user.is_staff:
            msg = "Must be a staff user to be able add tasks."
            raise GraphQLPermissionError(msg)


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)


schema = create_schema(query=Query, mutation=Mutation)
