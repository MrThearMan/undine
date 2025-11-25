from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import InterfaceField, InterfaceType
from undine.directives import Directive


class MyDirective(Directive, locations=[DirectiveLocation.INTERFACE]): ...


@MyDirective()
class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString))
