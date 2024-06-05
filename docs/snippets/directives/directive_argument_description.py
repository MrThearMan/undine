from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine.directives import Directive, DirectiveArgument


class VersionDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="version"):
    value = DirectiveArgument(GraphQLNonNull(GraphQLString), description="Version value.")
