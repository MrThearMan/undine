from graphql import GraphQLNonNull, GraphQLString

from undine import InterfaceField, InterfaceType


class Named(InterfaceType, schema_name="HasName"):
    name = InterfaceField(GraphQLNonNull(GraphQLString))
