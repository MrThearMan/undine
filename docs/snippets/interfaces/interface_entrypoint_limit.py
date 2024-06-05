from graphql import GraphQLNonNull, GraphQLString

from undine import Entrypoint, InterfaceField, InterfaceType, QueryType, RootType

from .models import Step, Task


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString))


class TaskType(QueryType[Task], interfaces=[Named]): ...


class StepType(QueryType[Step], interfaces=[Named]): ...


class Query(RootType):
    named = Entrypoint(Named, many=True, limit=10)
