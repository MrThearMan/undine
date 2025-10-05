from graphql import GraphQLNonNull, GraphQLString

from undine import InterfaceField, InterfaceType, QueryType

from .models import Task


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString))


@Named
class TaskType(QueryType[Task]): ...
