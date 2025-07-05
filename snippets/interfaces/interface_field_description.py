from graphql import GraphQLNonNull, GraphQLString

from undine import InterfaceField, InterfaceType


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString), description="The name of the object.")
