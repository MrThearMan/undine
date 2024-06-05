from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine import Entrypoint, RootType, create_schema
from undine.directives import Directive, DirectiveArgument


class VersionDirective(Directive, locations=[DirectiveLocation.SCHEMA], schema_name="version"):
    value = DirectiveArgument(GraphQLNonNull(GraphQLString))


class Query(RootType):
    @Entrypoint
    def example(self, value: str) -> str:
        return value


schema = create_schema(
    query=Query,
    schema_definition_directives=[VersionDirective(value="v1.0.0")],
)
