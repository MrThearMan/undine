from graphql import GraphQLNonNull, GraphQLString

from undine import InterfaceField, InterfaceType


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString), schema_name="name")
