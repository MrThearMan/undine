from graphql import GraphQLArgument, GraphQLNonNull, GraphQLString

from undine import InterfaceField, InterfaceType


class Named(InterfaceType):
    name = InterfaceField(
        GraphQLNonNull(GraphQLString),
        args={"name": GraphQLArgument(GraphQLNonNull(GraphQLString))},
    )
