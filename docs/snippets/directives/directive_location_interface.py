from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import InterfaceField, InterfaceType
from undine.directives import Directive, DirectiveArgument


class VersionDirective(Directive, locations=[DirectiveLocation.INTERFACE], schema_name="version"):
    value = DirectiveArgument(GraphQLNonNull(GraphQLString))


class Named(InterfaceType, directives=[VersionDirective(value="v1.0.0")]):
    name = InterfaceField(GraphQLNonNull(GraphQLString))
