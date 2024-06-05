from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import Entrypoint, RootType
from undine.directives import Directive, DirectiveArgument


class VersionDirective(
    Directive,
    locations=[DirectiveLocation.FIELD_DEFINITION],
    schema_name="version",
    is_repeatable=True,
):
    value = DirectiveArgument(GraphQLNonNull(GraphQLString))


class Query(RootType):
    @Entrypoint(directives=[VersionDirective(value="v1.0.0"), VersionDirective(value="v2.0.0")])
    def example(self) -> str:
        return "Example"
