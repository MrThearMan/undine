from undine import Entrypoint, GQLInfo, Input, MutationType, QueryType, RootType, create_schema
from undine.exceptions import GraphQLValidationError

from .models import Project, Step, Task


class ProjectType(QueryType[Project]): ...


class TaskType(QueryType[Task]): ...


class StepType(QueryType[Step]): ...


class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)


class TaskCreateMutation(MutationType[Task]):
    name = Input()

    @name.validate
    def validate_name(self, info: GQLInfo, value: str) -> None:
        if len(value) < 3:
            msg = "Name must be at least 3 characters."
            raise GraphQLValidationError(msg)


class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)


schema = create_schema(query=Query, mutation=Mutation)
