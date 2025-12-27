from graphql import DirectiveLocation

from undine.directives import Directive
from undine.typing import DjangoRequestProtocol


class NewDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION], schema_name="new"):
    @classmethod
    def __visible__(cls, request: DjangoRequestProtocol) -> bool:
        return request.user.is_superuser
