from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine.directives import Directive, DirectiveArgument
from undine.federation import FromContextDirective


class ScopedDirective(
    Directive,
    locations=[DirectiveLocation.FIELD_DEFINITION],
    schema_name="scoped",
):
    workspace = DirectiveArgument(
        GraphQLNonNull(GraphQLString),
        directives=[FromContextDirective(field="$workspace { id }")],
    )
