from graphql import GraphQLNonNull, GraphQLString

from undine import InterfaceField, InterfaceType


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString), cache_for_seconds=10, cache_per_user=True)
