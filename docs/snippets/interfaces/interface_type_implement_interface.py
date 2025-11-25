from graphql import GraphQLInt, GraphQLNonNull, GraphQLString

from undine import InterfaceField, InterfaceType


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString))


class Person(InterfaceType, interfaces=[Named]):
    age = InterfaceField(GraphQLNonNull(GraphQLInt))
