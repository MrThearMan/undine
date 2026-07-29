from graphql import DirectiveLocation

from undine import Directive
from undine.typing import DjangoRequestProtocol


class NewDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="new"):
    @classmethod
    def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
        return request.user.is_authenticated
