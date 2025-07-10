from undine import Entrypoint, GQLInfo, Input, MutationType, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError

from .models import Project, Step, Task


class ProjectType(QueryType[Project]): ...


class TaskType(QueryType[Task]): ...


class StepType(QueryType[Step]): ...


class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)


class TaskCreateMutation(MutationType[Task]):
    done = Input()

    @done.permissions
    def done_permissions(self, info: GQLInfo, value: bool) -> None:
        if not info.context.user.is_superuser:
            msg = "Must be a superuser to be able add done tasks."
            raise GraphQLPermissionError(msg)


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)


schema = create_schema(query=Query, mutation=Mutation)
