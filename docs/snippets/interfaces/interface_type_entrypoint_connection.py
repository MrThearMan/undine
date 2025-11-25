from graphql import GraphQLNonNull, GraphQLString

from undine import Entrypoint, InterfaceField, InterfaceType, QueryType, RootType
from undine.relay import Connection

from .models import Step, Task


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString))


@Named
class TaskType(QueryType[Task]): ...


@Named
class StepType(QueryType[Step]): ...


class Query(RootType):
    named = Entrypoint(Connection(Named))
