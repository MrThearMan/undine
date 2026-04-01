"""
### mypy_config
[mypy]
plugins = mypy_undine

### out
main:10: error: Directive "TestDirective" does not support location "OBJECT"  [misc]
"""

from graphql import DirectiveLocation

from undine import Directive, Entrypoint, RootType


class TestDirective(Directive, locations=[DirectiveLocation.FIELD_DEFINITION]): ...


@TestDirective()
class Query(RootType):
    @Entrypoint
    def foo(self) -> int:
        return 0
