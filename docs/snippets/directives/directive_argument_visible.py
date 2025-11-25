from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from undine.directives import Directive, DirectiveArgument
from undine.typing import DjangoRequestProtocol


class VersionDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="version"):
    value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    @value.visible
    def value_visible(self, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser
