from graphql import GraphQLNonNull, GraphQLString

from undine import InterfaceField, InterfaceType


class Named(InterfaceType, extensions={"foo": "bar"}):
    name = InterfaceField(GraphQLNonNull(GraphQLString))
