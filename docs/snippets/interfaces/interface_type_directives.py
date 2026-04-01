from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import Directive, InterfaceField, InterfaceType


class MyDirective(Directive, locations=[DirectiveLocation.INTERFACE]): ...


class Named(InterfaceType, directives=[MyDirective()]):
    name = InterfaceField(GraphQLNonNull(GraphQLString))
