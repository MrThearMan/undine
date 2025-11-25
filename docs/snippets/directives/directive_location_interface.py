from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import InterfaceField, InterfaceType
from undine.directives import Directive


class NewDirective(Directive, locations=[DirectiveLocation.INTERFACE], schema_name="new"): ...


class Named(InterfaceType, directives=[NewDirective()]):
    name = InterfaceField(GraphQLNonNull(GraphQLString))


# Alternatively...


@NewDirective()
class NamedAlt(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString))
