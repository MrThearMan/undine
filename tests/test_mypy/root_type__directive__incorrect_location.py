"""
### mypy_config
[mypy]
plugins = mypy_undine

### out
main:11: error: Directive "TestDirective" does not support location "OBJECT"  [misc]
"""

from graphql import DirectiveLocation

from undine.directives import Directive
from undine.entrypoint import Entrypoint, RootType


class TestDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


@TestDirective()
class Query(RootType):
    @Entrypoint
    def foo(self) -> int:
        return 0
