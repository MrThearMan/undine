from graphql import GraphQLNonNull, GraphQLString

from undine import InterfaceField, InterfaceType
from undine.typing import DjangoRequestProtocol


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString))

    @name.visible
    def name_visible(self, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser
