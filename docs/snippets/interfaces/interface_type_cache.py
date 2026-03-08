from graphql import GraphQLNonNull, GraphQLString

from undine import InterfaceField, InterfaceType


class Named(InterfaceType, cache_time=10, cache_per_user=True):
    name = InterfaceField(GraphQLNonNull(GraphQLString))
