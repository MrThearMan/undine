from graphql import GraphQLNonNull, GraphQLString

from undine import Entrypoint, GQLInfo, InterfaceField, InterfaceType, QueryType, RootType

from .models import Step, Task


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString))

    @classmethod
    def __process_results__(cls, instances: list[Task | Step], info: GQLInfo) -> list[Task | Step]:
        return sorted(instances, key=lambda x: x.name)


class TaskType(QueryType[Task], interfaces=[Named]): ...


class StepType(QueryType[Step], interfaces=[Named]): ...


class Query(RootType):
    named = Entrypoint(Named, many=True)
