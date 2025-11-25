from graphql import GraphQLNonNull, GraphQLString

from undine import InterfaceField, InterfaceType
from undine.typing import DjangoRequestProtocol


class Named(InterfaceType):
    name = InterfaceField(GraphQLNonNull(GraphQLString))

    @classmethod
    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser
