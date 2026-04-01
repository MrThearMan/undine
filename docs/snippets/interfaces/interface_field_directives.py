from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import Directive, InterfaceField, InterfaceType


class MyDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString), directives=[MyDirective()])
