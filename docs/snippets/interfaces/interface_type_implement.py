from graphql import GraphQLNonNull, GraphQLString

from undine import InterfaceField, InterfaceType, QueryType

from .models import Task


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString))


class TaskType(QueryType[Task], interfaces=[Named]): ...
