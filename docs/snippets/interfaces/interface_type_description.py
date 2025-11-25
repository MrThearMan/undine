from graphql import GraphQLNonNull, GraphQLString

from undine import InterfaceField, InterfaceType


class Named(InterfaceType):
    """Description."""

    name = InterfaceField(GraphQLNonNull(GraphQLString))
